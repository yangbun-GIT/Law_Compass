import json
import os
import random
import time
from datetime import datetime, timezone

import redis

from worker.job_processor import mark_failed, process_job

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
STREAM_KEY = os.getenv("REDIS_STREAM_KEY", "jobs:v1:stream")
GROUP = os.getenv("REDIS_STREAM_GROUP", "worker-group")
CONSUMER = f"worker-{os.getpid()}"
PENDING_IDLE_MS = int(os.getenv("REDIS_PENDING_IDLE_MS", "5000"))

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


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
                    process_job(job_id, job_type, r)
                    r.xack(STREAM_KEY, GROUP, msg_id)
                    r.setex(f"job:v1:{job_id}:status", 300, json.dumps({"status": "succeeded", "at": now_iso()}))
                except Exception as exc:
                    mark_failed(job_id, exc)
                    time.sleep(min(8.0, 2 ** random.randint(0, 3) + random.random()))
                    r.xack(STREAM_KEY, GROUP, msg_id)
                    r.setex(f"job:v1:{job_id}:status", 300, json.dumps({"status": "failed", "error": str(exc), "at": now_iso()}))


if __name__ == "__main__":
    main_loop()
