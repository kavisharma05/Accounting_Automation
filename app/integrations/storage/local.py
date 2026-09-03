import os
from pathlib import Path

from app.core.config import settings
from app.integrations.protocols import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_path: str | None = None):
        self.base = Path(base_path or settings.local_storage_path)
        self.base.mkdir(parents=True, exist_ok=True)

    async def put(self, key: str, content: bytes, mime_type: str) -> str:
        path = self.base / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        meta_path = path.with_suffix(path.suffix + ".meta")
        meta_path.write_text(mime_type)
        return key

    async def get(self, key: str) -> tuple[bytes, str]:
        path = self.base / key
        mime = "application/octet-stream"
        meta_path = path.with_suffix(path.suffix + ".meta")
        if meta_path.exists():
            mime = meta_path.read_text()
        return path.read_bytes(), mime

    async def delete(self, key: str) -> None:
        path = self.base / key
        if path.exists():
            os.remove(path)
