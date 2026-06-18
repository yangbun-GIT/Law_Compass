import json
import multiprocessing as mp
import os
import random
import time
from datetime import datetime, timezone
from typing import Mapping

import redis

from worker.job_processor import mark_failed, process_job

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
STREAM_KEY = os.getenv("REDIS_STREAM_KEY", "jobs:v1:stream")
GROUP = os.getenv("REDIS_STREAM_GROUP", "worker-group")
CONSUMER = f"worker-{os.getpid()}"
PENDING_IDLE_MS = int(os.getenv("REDIS_PENDING_IDLE_MS", "5000"))

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


class WorkerJobTimeoutError(TimeoutError):
    pass


def _float_env(values: Mapping[str, str | None], key: str) -> float | None:
    raw = str(values.get(key) or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def job_timeout_seconds(job_type: str | None, env: Mapping[str, str | None] | None = None) -> float:
    values = os.environ if env is None else env
    normalized_type = str(job_type or "").strip().lower()

    if normalized_type == "video_preprocess":
        explicit = _float_env(values, "WORKER_VIDEO_PREPROCESS_TIMEOUT_SEC")
        if explicit is not None:
            return max(30.0, explicit)
    elif normalized_type == "video_analyze":
        explicit = _float_env(values, "WORKER_VIDEO_ANALYZE_TIMEOUT_SEC")
        if explicit is not None:
            return max(30.0, explicit)

    explicit = _float_env(values, "WORKER_JOB_TIMEOUT_SEC")
    if explicit is not None:
        return max(30.0, explicit)

    return 240.0


def init_group() -> None:
    try:
        r.xgroup_create(STREAM_KEY, GROUP, id="0", mkstream=True)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_stale_pending_entries():
    try:
        result = r.xautoclaim(
            STREAM_KEY,
            GROUP,
            CONSUMER,
            PENDING_IDLE_MS,
            "0-0",
            count=1,
        )
    except redis.ResponseError as exc:
        print(json.dumps({"event": "redis_pending_reclaim_unavailable", "error": str(exc), "at": now_iso()}))
        return []

    messages = result[1] if result and len(result) > 1 else []
    if not messages:
        return []
    return [(STREAM_KEY, messages)]


def read_next_entries():
    pending = read_stale_pending_entries()
    if pending:
        return pending
    return r.xreadgroup(groupname=GROUP, consumername=CONSUMER, streams={STREAM_KEY: ">"}, count=1, block=5000)


def _process_job_child(job_id: str, job_type: str) -> None:
    child_redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    process_job(job_id, job_type, child_redis)


def run_job_with_timeout(job_id: str, job_type: str) -> None:
    timeout = job_timeout_seconds(job_type)
    proc = mp.Process(target=_process_job_child, args=(job_id, job_type), daemon=False)
    proc.start()
    proc.join(timeout)

    if proc.is_alive():
        proc.terminate()
        proc.join(5)
        if proc.is_alive():
            proc.kill()
            proc.join(2)
        raise WorkerJobTimeoutError(f"{job_type or 'unknown'} job exceeded {int(timeout)}s timeout")

    if proc.exitcode != 0:
        raise RuntimeError(f"{job_type or 'unknown'} job child exited with code {proc.exitcode}")


def main_loop() -> None:
    init_group()
    while True:
        entries = read_next_entries()
        if not entries:
            continue

        for _, messages in entries:
            for msg_id, fields in messages:
                job_id = fields.get("job_id")
                job_type = fields.get("job_type")
                try:
                    if not job_id:
                        raise ValueError("missing job_id in redis stream message")
                    run_job_with_timeout(job_id, job_type or "")
                    r.xack(STREAM_KEY, GROUP, msg_id)
                    r.setex(f"job:v1:{job_id}:status", 300, json.dumps({"status": "succeeded", "at": now_iso()}))
                except Exception as exc:
                    if job_id:
                        mark_failed(job_id, exc)
                    time.sleep(min(8.0, 2 ** random.randint(0, 3) + random.random()))
                    r.xack(STREAM_KEY, GROUP, msg_id)
                    if job_id:
                        r.setex(f"job:v1:{job_id}:status", 300, json.dumps({"status": "failed", "error": str(exc), "at": now_iso()}))


if __name__ == "__main__":
    main_loop()
