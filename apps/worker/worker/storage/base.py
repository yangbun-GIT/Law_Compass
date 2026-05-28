from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, Protocol


class StorageAdapter(Protocol):
    driver: str

    def put_file(self, local_path: str | Path, destination_path: str, metadata: dict | None = None) -> dict:
        ...

    def put_stream(self, stream: BinaryIO, destination_path: str, metadata: dict | None = None) -> dict:
        ...

    def get_file(self, remote_path: str, local_destination: str | Path) -> None:
        ...

    def get_stream(self, remote_path: str) -> BinaryIO:
        ...

    def exists(self, remote_path: str) -> bool:
        ...

    def delete(self, remote_path: str) -> None:
        ...

    def move(self, source_path: str, destination_path: str) -> None:
        ...

    def list(self, prefix: str) -> list[str]:
        ...

    def get_public_download_url(self, remote_path: str) -> str | None:
        ...

    def create_download_token(self, remote_path: str) -> str | None:
        ...

    def normalize_path(self, value: str) -> str:
        ...

    def safe_join(self, *parts: str) -> str:
        ...


def normalize_storage_key(value: str) -> str:
    normalized = str(value or "").replace("\\", "/").lstrip("/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    if not normalized or "\x00" in normalized:
        raise ValueError("INVALID_STORAGE_PATH")
    parts = normalized.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("INVALID_STORAGE_PATH")
    return "/".join(parts)


def safe_join_posix(base_dir: str, key: str) -> str:
    base = str(base_dir or "").replace("\\", "/").rstrip("/")
    if not base.startswith("/"):
        raise ValueError("INVALID_STORAGE_BASE")
    return f"{base}/{normalize_storage_key(key)}"


def frame_key(case_id: str, upload_id: str, frame_name: str) -> str:
    return normalize_storage_key(f"processed/frames/{case_id}/{upload_id}/{Path(frame_name).name}")
