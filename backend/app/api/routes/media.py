from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_csrf, require_current_user, require_episode
from app.api.errors import APIError
from app.core.config import settings
from app.db.session import get_db
from app.models import MediaAttachment, User
from app.schemas.media import MediaAttachmentRead, MediaFactsUpdate
from app.services.media_storage import cleanup_path, retry_pending

router = APIRouter(tags=["local-media"])
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "video/mp4", "video/webm", "application/pdf", "text/plain"}

def _valid_content(media_type: str, head: bytes, path: Path) -> bool:
    if media_type == "image/jpeg": return head.startswith(b"\xff\xd8\xff")
    if media_type == "image/png": return head.startswith(b"\x89PNG\r\n\x1a\n")
    if media_type == "image/webp": return head.startswith(b"RIFF") and head[8:12] == b"WEBP"
    if media_type == "application/pdf": return head.startswith(b"%PDF-")
    if media_type == "video/mp4": return len(head) >= 12 and head[4:8] == b"ftyp"
    if media_type == "video/webm": return head.startswith(b"\x1aE\xdf\xa3")
    if media_type == "text/plain":
        try:
            return b"\x00" not in path.read_bytes() and bool(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            return False
    return False

def _attachment(db: Session, attachment_id: int, user: User) -> MediaAttachment:
    item = db.scalar(select(MediaAttachment).where(MediaAttachment.id == attachment_id))
    if item is None:
        raise APIError(404, "MEDIA_NOT_FOUND", "Media attachment not found")
    require_episode(db, item.episode_id, user)
    return item

@router.get("/episodes/{episode_id}/media", response_model=list[MediaAttachmentRead])
def list_media(episode_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    retry_pending(settings.media_dir)
    require_episode(db, episode_id, user)
    items = list(db.scalars(select(MediaAttachment).where(MediaAttachment.episode_id == episode_id).order_by(MediaAttachment.id.desc())).all())
    for item in items:
        path = settings.media_dir / item.storage_key
        if item.status == "AVAILABLE" and not path.is_file():
            item.status = "MISSING"
    db.commit()
    return items

@router.post("/episodes/{episode_id}/media", response_model=MediaAttachmentRead, status_code=201)
async def upload_media(request: Request, episode_id: int, filename: str = Header(alias="X-Filename"), content_type: str = Header(alias="Content-Type"), db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    require_episode(db, episode_id, user, for_update=True)
    normalized = content_type.split(";", 1)[0].strip().lower()
    if normalized not in ALLOWED_TYPES:
        raise APIError(415, "MEDIA_TYPE_NOT_ALLOWED", "Unsupported media type")
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > settings.media_max_bytes:
        raise APIError(413, "MEDIA_SIZE_INVALID", "Media must be non-empty and within the configured size limit")
    safe_name = Path(filename).name[:255]
    if not safe_name:
        raise APIError(422, "MEDIA_FILENAME_REQUIRED", "A filename is required")
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    storage_key = uuid4().hex
    path = settings.media_dir / storage_key
    temporary = settings.media_dir / f".{storage_key}.uploading"
    digest = sha256(); size = 0; head = b""
    try:
        with temporary.open("xb") as handle:
            async for chunk in request.stream():
                size += len(chunk)
                if size > settings.media_max_bytes:
                    raise APIError(413, "MEDIA_SIZE_INVALID", "Media must be non-empty and within the configured size limit")
                if len(head) < 32: head += chunk[:32 - len(head)]
                digest.update(chunk); handle.write(chunk)
        if size == 0:
            raise APIError(413, "MEDIA_SIZE_INVALID", "Media must be non-empty and within the configured size limit")
        if not _valid_content(normalized, head, temporary):
            raise APIError(415, "MEDIA_CONTENT_MISMATCH", "File contents do not match the declared media type")
        temporary.replace(path)
        item = MediaAttachment(episode_id=episode_id, original_filename=safe_name, media_type=normalized, byte_size=size, sha256=digest.hexdigest(), storage_key=storage_key)
        db.add(item); db.commit()
    except Exception:
        db.rollback()
        if temporary.is_file(): temporary.unlink()
        if path.is_file(): path.unlink()
        raise
    db.refresh(item)
    return item

@router.patch("/media/{attachment_id}", response_model=MediaAttachmentRead)
def update_media(attachment_id: int, payload: MediaFactsUpdate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    item = _attachment(db, attachment_id, user)
    item.observable_facts = payload.observable_facts.strip() if payload.observable_facts and payload.observable_facts.strip() else None
    db.commit(); db.refresh(item); return item

@router.get("/media/{attachment_id}/content")
def get_media_content(attachment_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    item = _attachment(db, attachment_id, user)
    path = settings.media_dir / item.storage_key
    if not path.is_file():
        if item.status != "MISSING": item.status = "MISSING"; db.commit()
        raise APIError(410, "MEDIA_FILE_MISSING", "Stored media file is missing")
    data = path.read_bytes()
    if sha256(data).hexdigest() != item.sha256:
        item.status = "CORRUPT"; db.commit()
        raise APIError(409, "MEDIA_FILE_CORRUPT", "Stored media file failed integrity verification")
    return FileResponse(path, media_type=item.media_type, filename=item.original_filename, headers={"X-Content-Type-Options": "nosniff"})

@router.delete("/media/{attachment_id}", status_code=204)
def delete_media(attachment_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    item = _attachment(db, attachment_id, user)
    path = settings.media_dir / item.storage_key
    quarantine = settings.media_dir / f".{item.storage_key}.deleting"
    moved = False
    try:
        if path.is_file(): path.replace(quarantine); moved = True
        db.delete(item); db.commit()
    except Exception:
        db.rollback()
        if moved and quarantine.is_file(): quarantine.replace(path)
        raise
    if moved and quarantine.is_file():
        cleanup_path(quarantine, settings.media_dir)
