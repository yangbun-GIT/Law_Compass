from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO

from worker.storage.base import normalize_storage_key


class LocalStorageAdapter:
    driver = "local"

    def __init__(self, root_dir: str = "/app/storage") -> None:
        self.root_dir = Path(root_dir)

    def normalize_path(self, value: str) -> str:
        return normalize_storage_key(value)

    def safe_join(self, *parts: str) -> str:
        key = normalize_storage_key("/".join(parts))
        return str(self.root_dir / key)

    def put_file(self, local_path: str | Path, destination_path: str, metadata: dict | None = None) -> dict:
        key = normalize_storage_key(destination_path)
        target = Path(self.safe_join(key))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local_path, target)
        return {"storage_driver": self.driver, "storage_key": key, "storage_path": str(target), "size_bytes": target.stat().st_size, **(metadata or {})}

    def put_stream(self, stream: BinaryIO, destination_path: str, metadata: dict | None = None) -> dict:
        key = normalize_storage_key(destination_path)
        target = Path(self.safe_join(key))
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as out:
            shutil.copyfileobj(stream, out)
        return {"storage_driver": self.driver, "storage_key": key, "storage_path": str(target), "size_bytes": target.stat().st_size, **(metadata or {})}

    def get_file(self, remote_path: str, local_destination: str | Path) -> None:
        source = Path(self.safe_join(remote_path))
        target = Path(local_destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    def get_stream(self, remote_path: str) -> BinaryIO:
        return Path(self.safe_join(remote_path)).open("rb")

    def exists(self, remote_path: str) -> bool:
        return Path(self.safe_join(remote_path)).exists()

    def delete(self, remote_path: str) -> None:
        Path(self.safe_join(remote_path)).unlink(missing_ok=True)

    def move(self, source_path: str, destination_path: str) -> None:
        source = Path(self.safe_join(source_path))
        target = Path(self.safe_join(destination_path))
        target.parent.mkdir(parents=True, exist_ok=True)
        source.replace(target)

    def list(self, prefix: str) -> list[str]:
        root = Path(self.safe_join(prefix))
        if not root.exists():
            return []
        return [normalize_storage_key(str(path.relative_to(self.root_dir))) for path in root.rglob("*") if path.is_file()]

    def get_public_download_url(self, remote_path: str) -> str | None:
        normalize_storage_key(remote_path)
        return None

    def create_download_token(self, remote_path: str) -> str | None:
        normalize_storage_key(remote_path)
        return None
