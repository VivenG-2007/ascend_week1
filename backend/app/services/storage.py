"""Original-file storage: Supabase Storage (cloud) with local-directory fallback for dev."""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

import httpx

from app.config import BACKEND_DIR, get_settings

log = logging.getLogger("campusvoice.storage")
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_filename(name: str) -> str:
    """Strip directories and unsafe characters (prevents path traversal)."""
    base = re.split(r"[\\/]", name or "")[-1]
    base = _SAFE.sub("_", base).strip("._") or "upload"
    return base[:100]


class Storage(Protocol):
    def save(self, path: str, data: bytes, content_type: str) -> str: ...
    def read(self, path: str) -> bytes: ...
    def public_url(self, path: str) -> str | None: ...


class LocalStorage:
    def __init__(self, root: str) -> None:
        p = Path(root)
        self.root = (p if p.is_absolute() else BACKEND_DIR / p).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        log.info("LocalStorage: root=%s", self.root)

    def _resolve(self, path: str) -> Path:
        target = (self.root / path).resolve()
        if self.root not in target.parents:
            raise ValueError("Invalid storage path")
        return target

    def save(self, path: str, data: bytes, content_type: str) -> str:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        log.debug("LocalStorage.save: %s (%d bytes)", path, len(data))
        return path

    def read(self, path: str) -> bytes:
        log.debug("LocalStorage.read: %s", path)
        return self._resolve(path).read_bytes()

    def public_url(self, path: str) -> str | None:
        return None


class SupabaseStorage:
    def __init__(self, url: str, key: str, bucket: str, client: httpx.Client | None = None) -> None:
        self.base = url.rstrip("/") + "/storage/v1"
        self.bucket = bucket
        self.http = client or httpx.Client(timeout=30)
        self.headers = {"Authorization": f"Bearer {key}", "apikey": key}
        log.info("SupabaseStorage: url=%s bucket=%s", url, bucket)

    def save(self, path: str, data: bytes, content_type: str) -> str:
        log.debug("SupabaseStorage.save: path=%s size=%d bytes", path, len(data))
        r = self.http.post(
            f"{self.base}/object/{self.bucket}/{quote(path)}",
            content=data,
            headers={**self.headers, "Content-Type": content_type, "x-upsert": "true"},
        )
        if r.status_code >= 300:
            log.error("Supabase Storage upload failed HTTP %d path=%s", r.status_code, path)
            raise RuntimeError(f"Supabase Storage upload failed (HTTP {r.status_code})")
        log.debug("SupabaseStorage.save: OK path=%s", path)
        return path

    def read(self, path: str) -> bytes:
        log.debug("SupabaseStorage.read: path=%s", path)
        r = self.http.get(
            f"{self.base}/object/{self.bucket}/{quote(path)}", headers=self.headers
        )
        if r.status_code >= 300:
            log.error("Supabase Storage download failed HTTP %d path=%s", r.status_code, path)
            raise RuntimeError(f"Supabase Storage download failed (HTTP {r.status_code})")
        log.debug("SupabaseStorage.read: %d bytes for path=%s", len(r.content), path)
        return r.content

    def public_url(self, path: str) -> str | None:
        r = self.http.post(
            f"{self.base}/object/sign/{self.bucket}/{quote(path)}",
            json={"expiresIn": 300},
            headers=self.headers,
        )
        if r.status_code >= 300:
            log.warning("SupabaseStorage.public_url: failed HTTP %d path=%s", r.status_code, path)
            return None
        signed = r.json().get("signedURL") or r.json().get("signedUrl")
        if not signed:
            return None
        url = self.base + signed if signed.startswith("/") else signed
        log.debug("SupabaseStorage.public_url: signed URL for path=%s", path)
        return url


@lru_cache
def get_storage() -> Storage:
    s = get_settings()
    if s.supabase_url and s.supabase_service_role_key:
        log.info("Using Supabase cloud storage")
        return SupabaseStorage(s.supabase_url, s.supabase_service_role_key, s.supabase_storage_bucket)
    log.info("Using local file storage (Supabase not configured)")
    return LocalStorage(s.local_storage_directory)
