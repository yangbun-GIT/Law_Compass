from __future__ import annotations

import os

from worker.storage.local_storage import LocalStorageAdapter
from worker.storage.nas_sftp_storage import NasSftpStorageAdapter
from worker.storage.s3_storage import S3StorageAdapter


def create_storage_adapter(driver: str | None = None):
    selected = (driver or os.getenv("STORAGE_DRIVER") or os.getenv("STORAGE_PROVIDER") or "local").strip().lower()
    if selected == "nas_sftp":
        return NasSftpStorageAdapter(
            host=os.getenv("NAS_HOST", ""),
            port=int(os.getenv("NAS_PORT", "22")),
            username=os.getenv("NAS_USER", ""),
            password=os.getenv("NAS_PASSWORD") or None,
            private_key_path=os.getenv("NAS_PRIVATE_KEY_PATH") or None,
            private_key_passphrase=os.getenv("NAS_PRIVATE_KEY_PASSPHRASE") or None,
            base_dir=os.getenv("NAS_BASE_DIR", "/lawcompass"),
        )
    if selected == "s3":
        return S3StorageAdapter()
    return LocalStorageAdapter(os.getenv("LOCAL_STORAGE_ROOT", "/app/storage"))
