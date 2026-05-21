import json
import mimetypes
import sys
import time
import uuid
from pathlib import Path
from urllib import request, error


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://localhost"
SAMPLE_JSON = ROOT / "sample_data" / "sample_accident.json"
SAMPLE_VIDEO = ROOT / "sample_data" / "sample_video.mp4"


def http_json(method: str, path: str, payload: dict | None = None, token: str | None = None):
    data = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json", "Idempotency-Key": str(uuid.uuid4())}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        if exc.code == 409 and path == "/api/v1/auth/signup":
            return {"already_exists": True}
        raise RuntimeError(f"{method} {path} failed: {exc.code} {body}") from exc


def multipart_upload(path: str, case_id: str, file_path: Path, token: str):
    boundary = f"----lawcompass{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(file_path.name)[0] or "video/mp4"
    parts = []
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"case_id\"\r\n\r\n{case_id}\r\n".encode())
    header = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"{file_path.name}\"\r\n"
        f"Content-Type: {mime}\r\n\r\n"
    ).encode()
    footer = f"\r\n--{boundary}--\r\n".encode()
    body = b"".join(parts) + header + file_path.read_bytes() + footer
    req = request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Idempotency-Key": str(uuid.uuid4()),
        },
        method="POST",
    )
    with request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    if not SAMPLE_VIDEO.exists():
        print(f"sample video missing: {SAMPLE_VIDEO}")
        print("Create one with: ffmpeg -y -f lavfi -i testsrc=size=320x180:rate=10 -t 2 -pix_fmt yuv420p sample_data/sample_video.mp4")
        sys.exit(2)

    sample = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
    user = sample["user"]
    case_payload = sample["case"]

    http_json("POST", "/api/v1/auth/signup", user)
    login = http_json("POST", "/api/v1/auth/login", {"email": user["email"], "password": user["password"]})
    token = login["access_token"]
    print("login ok")

    created = http_json("POST", "/api/v1/cases", case_payload, token)
    case_id = created["case"]["id"]
    print(f"case_id={case_id}")

    uploaded = multipart_upload("/api/v1/uploads/local", case_id, SAMPLE_VIDEO, token)
    upload_id = uploaded["upload_id"]
    print(f"upload_id={upload_id}")

    completed = http_json("POST", "/api/v1/uploads/complete", {"upload_id": upload_id}, token)
    print(f"preprocess_job_id={completed['job_id']}")

    result = None
    for _ in range(40):
        jobs = http_json("GET", f"/api/v1/cases/{case_id}/jobs", token=token)
        statuses = [(job["type"], job["status"]) for job in jobs.get("items", [])]
        print(f"jobs={statuses}")
        try:
            result = http_json("GET", f"/api/v1/cases/{case_id}/report", token=token)
            break
        except Exception:
            time.sleep(2)

    if not result:
        raise RuntimeError("result was not created in time")
    print(json.dumps(result["report"], ensure_ascii=False, indent=2)[:4000])

    evidence = http_json("GET", f"/api/v1/cases/{case_id}/evidence", token=token)
    print(f"evidence_count={len(evidence.get('evidence', []))}")


if __name__ == "__main__":
    main()
