import uuid
import os
from pathlib import Path
from config import settings


ALLOWED_MIME = {
    "image/jpeg", "image/png", "image/gif",
    "image/webp", "image/svg+xml",
}
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}


def validate_upload(filename: str, content_type: str, size: int) -> str | None:
    """Returns error string or None if valid."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return f"File type not allowed: {ext}"
    if content_type not in ALLOWED_MIME:
        return f"MIME type not allowed: {content_type}"
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if size > max_bytes:
        return f"File too large (max {settings.MAX_UPLOAD_MB} MB)"
    return None


def save_upload(file_bytes: bytes, filename: str, system_id: int) -> tuple[str, str]:
    """Save bytes to media folder. Returns (relative_path, url)."""
    ext = Path(filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex[:12]}{ext}"
    folder = Path(settings.MEDIA_PATH) / str(system_id)
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / unique_name
    dest.write_bytes(file_bytes)
    rel  = f"{system_id}/{unique_name}"
    url  = f"/media/{rel}"
    return rel, url


def delete_file(path: str):
    full = Path(settings.MEDIA_PATH) / path
    if full.exists():
        full.unlink()
