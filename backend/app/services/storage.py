"""
Document Storage Service (Supabase Storage Cloud or Local Filesystem)
"""
import os
import uuid
import logging
from pathlib import Path
from typing import Tuple
from app.config import settings, PROJECT_ROOT

logger = logging.getLogger("campusvoice.storage")

UPLOADS_DIR = Path(PROJECT_ROOT) / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

def save_document_file(file_bytes: bytes, original_filename: str, content_type: str) -> Tuple[str, str]:
    """
    Saves the file to Supabase Storage if configured, or local uploads directory.
    Returns (file_url, storage_path).
    """
    ext = Path(original_filename).suffix.lower() or ".bin"
    unique_filename = f"{uuid.uuid4()}{ext}"

    # 1. Supabase Storage (Cloud)
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        try:
            from supabase import create_client
            supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            bucket = settings.SUPABASE_STORAGE_BUCKET
            
            # Upload to bucket
            res = supabase.storage.from_(bucket).upload(
                path=unique_filename,
                file=file_bytes,
                file_options={"content-type": content_type}
            )
            public_url = supabase.storage.from_(bucket).get_public_url(unique_filename)
            logger.info(f"[SUPABASE STORAGE] Successfully uploaded {unique_filename} to bucket '{bucket}'.")
            return public_url, unique_filename
        except Exception as e:
            logger.warning(f"[SUPABASE STORAGE] Cloud upload failed: {e}. Falling back to local storage.")

    # 2. Local Filesystem Fallback
    local_path = UPLOADS_DIR / unique_filename
    with open(local_path, "wb") as f:
        f.write(file_bytes)

    logger.info(f"[LOCAL STORAGE] Saved document to {local_path}")
    return f"/uploads/{unique_filename}", str(local_path)
