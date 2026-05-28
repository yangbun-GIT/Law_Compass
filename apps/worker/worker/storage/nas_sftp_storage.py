from __future__ import annotations

from pathlib import Path
from typing import Any, BinaryIO

from worker.storage.base import normalize_storage_key, safe_join_posix


class NasSftpStorageAdapter:
    driver = "nas_sftp"

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str | None = None,
        private_key_path: str | None = None,
        private_key_passphrase: str | None = None,
        base_dir: str = "/lawcompass",
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.private_key_path = private_key_path
        self.private_key_passphrase = private_key_passphrase
        self.base_dir = base_dir

    def normalize_path(self, value: str) -> str:
        return normalize_storage_key(value)

    def safe_join(self, *parts: str) -> str:
        return safe_join_posix(self.base_dir, normalize_storage_key("/".join(parts)))

    def put_file(self, local_path: str | Path, destination_path: str, metadata: dict | None = None) -> dict:
        key = normalize_storage_key(destination_path)
        remote = self.safe_join(key)
        with self._client() as sftp:
            self._mkdir_p(sftp, str(Path(remote).parent).replace("\\", "/"))
            sftp.put(str(local_path), remote)
        size = Path(local_path).stat().st_size
        return {"storage_driver": self.driver, "storage_key": key, "storage_path": remote, "size_bytes": size, **(metadata or {})}

    def put_stream(self, stream: BinaryIO, destination_path: str, metadata: dict | None = None) -> dict:
        key = normalize_storage_key(destination_path)
        remote = self.safe_join(key)
        with self._client() as sftp:
            self._mkdir_p(sftp, str(Path(remote).parent).replace("\\", "/"))
            with sftp.open(remote, "wb") as out:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            size = sftp.stat(remote).st_size
        return {"storage_driver": self.driver, "storage_key": key, "storage_path": remote, "size_bytes": int(size), **(metadata or {})}

    def get_file(self, remote_path: str, local_destination: str | Path) -> None:
        key = normalize_storage_key(remote_path)
        target = Path(local_destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        with self._client() as sftp:
            sftp.get(self.safe_join(key), str(target))

    def get_stream(self, remote_path: str) -> BinaryIO:
        key = normalize_storage_key(remote_path)
        context = self._client()
        sftp = context.__enter__()
        stream = sftp.open(self.safe_join(key), "rb")
        return _SftpReadStream(stream, context)

    def exists(self, remote_path: str) -> bool:
        try:
            with self._client() as sftp:
                sftp.stat(self.safe_join(remote_path))
            return True
        except FileNotFoundError:
            return False

    def delete(self, remote_path: str) -> None:
        with self._client() as sftp:
            try:
                sftp.remove(self.safe_join(remote_path))
            except FileNotFoundError:
                return

    def move(self, source_path: str, destination_path: str) -> None:
        with self._client() as sftp:
            destination = self.safe_join(destination_path)
            self._mkdir_p(sftp, str(Path(destination).parent).replace("\\", "/"))
            sftp.rename(self.safe_join(source_path), destination)

    def list(self, prefix: str) -> list[str]:
        key = normalize_storage_key(prefix)
        remote = self.safe_join(key)
        with self._client() as sftp:
            try:
                return [normalize_storage_key(f"{key}/{name}") for name in sftp.listdir(remote)]
            except FileNotFoundError:
                return []

    def get_public_download_url(self, remote_path: str) -> str | None:
        normalize_storage_key(remote_path)
        return None

    def create_download_token(self, remote_path: str) -> str | None:
        normalize_storage_key(remote_path)
        return None

    def _client(self) -> Any:
        try:
            import paramiko
        except ModuleNotFoundError as exc:
            raise RuntimeError("PARAMIKO_NOT_INSTALLED") from exc

        transport = paramiko.Transport((self.host, self.port))
        if self.private_key_path:
            key = _load_private_key(paramiko, self.private_key_path, self.private_key_passphrase or None)
            transport.connect(username=self.username, pkey=key)
        else:
            transport.connect(username=self.username, password=self.password or "")
        sftp = paramiko.SFTPClient.from_transport(transport)
        return _SftpContext(sftp, transport)

    def _mkdir_p(self, sftp: Any, remote_dir: str) -> None:
        current = ""
        for part in remote_dir.split("/"):
            if not part:
                current = "/"
                continue
            current = f"{current.rstrip('/')}/{part}"
            try:
                sftp.stat(current)
            except FileNotFoundError:
                sftp.mkdir(current)


def _load_private_key(paramiko: Any, private_key_path: str, passphrase: str | None) -> Any:
    key_types = [
        paramiko.Ed25519Key,
        paramiko.ECDSAKey,
        paramiko.RSAKey,
        paramiko.DSSKey,
    ]
    last_error: Exception | None = None
    for key_type in key_types:
        try:
            return key_type.from_private_key_file(private_key_path, password=passphrase)
        except Exception as exc:  # pragma: no cover - key format depends on operator setup.
            last_error = exc
    raise RuntimeError("NAS_PRIVATE_KEY_UNREADABLE") from last_error


class _SftpContext:
    def __init__(self, sftp: Any, transport: Any) -> None:
        self.sftp = sftp
        self.transport = transport

    def __enter__(self) -> Any:
        return self.sftp

    def __exit__(self, *_args: Any) -> None:
        self.sftp.close()
        self.transport.close()


class _SftpReadStream:
    def __init__(self, stream: Any, context: _SftpContext) -> None:
        self.stream = stream
        self.context = context

    def read(self, *args: Any) -> bytes:
        return self.stream.read(*args)

    def close(self) -> None:
        try:
            self.stream.close()
        finally:
            self.context.__exit__(None, None, None)

    def __enter__(self) -> "_SftpReadStream":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()
