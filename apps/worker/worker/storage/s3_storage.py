from __future__ import annotations


class S3StorageAdapter:
    driver = "s3"

    def normalize_path(self, value: str) -> str:
        return value

    def safe_join(self, *parts: str) -> str:
        return "/".join(part.strip("/") for part in parts if part)

    def put_file(self, *_args, **_kwargs) -> dict:
        raise RuntimeError("S3_STORAGE_NOT_ENABLED")

    def put_stream(self, *_args, **_kwargs) -> dict:
        raise RuntimeError("S3_STORAGE_NOT_ENABLED")

    def get_file(self, *_args, **_kwargs) -> None:
        raise RuntimeError("S3_STORAGE_NOT_ENABLED")

    def get_stream(self, *_args, **_kwargs):
        raise RuntimeError("S3_STORAGE_NOT_ENABLED")

    def exists(self, *_args, **_kwargs) -> bool:
        raise RuntimeError("S3_STORAGE_NOT_ENABLED")

    def delete(self, *_args, **_kwargs) -> None:
        raise RuntimeError("S3_STORAGE_NOT_ENABLED")

    def move(self, *_args, **_kwargs) -> None:
        raise RuntimeError("S3_STORAGE_NOT_ENABLED")

    def list(self, *_args, **_kwargs) -> list[str]:
        raise RuntimeError("S3_STORAGE_NOT_ENABLED")

    def get_public_download_url(self, *_args, **_kwargs) -> str | None:
        raise RuntimeError("S3_STORAGE_NOT_ENABLED")

    def create_download_token(self, *_args, **_kwargs) -> str | None:
        raise RuntimeError("S3_STORAGE_NOT_ENABLED")
