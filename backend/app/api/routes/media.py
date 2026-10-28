from hashlib import sha256
from pathlib import Path
from uuid import uuid4
from urllib.parse import unquote

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_csrf, require_current_user, require_episode, require_life_event, require_pet
from app.api.errors import APIError
from app.core.config import settings
from app.db.session import get_db
from app.models import MediaAttachment, MediaAttachmentRevision, Pet, User
from app.schemas.media import MediaAttachmentRead, MediaCandidateUpdate, MediaFactsUpdate, MediaMetadataUpdate
from app.services.media_storage import cleanup_path, retry_pending
from app.services.relationships import get_relationship_event

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
    item = db.scalar(
        select(MediaAttachment)
        .where(MediaAttachment.id == attachment_id)
        .options(selectinload(MediaAttachment.revisions))
        .execution_options(populate_existing=True)
    )
    if item is None:
        raise APIError(404, "MEDIA_NOT_FOUND", "Media attachment not found")
    pet = db.scalar(select(Pet.id).where(Pet.id == item.pet_id, Pet.owner_user_id == user.id, Pet.archived_at.is_(None)))
    if pet is None:
        raise APIError(404, "MEDIA_NOT_FOUND", "Media attachment not found")
    return item

def _append_revision(db: Session, item: MediaAttachment, summary: str | None) -> None:
    db.add(MediaAttachmentRevision(
        attachment_id=item.id,
        revision_number=max((revision.revision_number for revision in item.revisions), default=0) + 1,
        captured_at=item.captured_at,
        owner_caption=item.owner_caption,
        ai_candidate_observation=item.ai_candidate_observation,
        ai_candidate_status=item.ai_candidate_status,
        change_summary=summary,
    ))

def _list(db: Session, user: User, field, record_id: int) -> list[MediaAttachment]:
    items = list(db.scalars(select(MediaAttachment).where(field == record_id).options(selectinload(MediaAttachment.revisions)).order_by(MediaAttachment.id.desc())).all())
    for item in items:
        if db.scalar(select(Pet.id).where(Pet.id == item.pet_id, Pet.owner_user_id == user.id, Pet.archived_at.is_(None))) is None:
            raise APIError(404, "MEDIA_RECORD_NOT_FOUND", "Media record not found")
        path = settings.media_dir / item.storage_key
        if item.status == "AVAILABLE" and not path.is_file(): item.status = "MISSING"
    db.commit(); return items

@router.get("/episodes/{episode_id}/media", response_model=list[MediaAttachmentRead])
def list_media(episode_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    retry_pending(settings.media_dir)
    require_episode(db, episode_id, user)
    return _list(db, user, MediaAttachment.episode_id, episode_id)

@router.get("/pets/{pet_id}/media", response_model=list[MediaAttachmentRead])
def list_pet_media(pet_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    retry_pending(settings.media_dir); require_pet(db, pet_id, user); return _list(db, user, MediaAttachment.pet_id, pet_id)

@router.get("/life-events/{event_id}/media", response_model=list[MediaAttachmentRead])
def list_life_event_media(event_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    retry_pending(settings.media_dir); require_life_event(db, event_id, user); return _list(db, user, MediaAttachment.life_event_id, event_id)

@router.get("/relationship-events/{event_id}/media", response_model=list[MediaAttachmentRead])
def list_relationship_event_media(event_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    retry_pending(settings.media_dir)
    if get_relationship_event(db, event_id, user) is None: raise APIError(404, "RELATIONSHIP_EVENT_NOT_FOUND", "Relationship event not found")
    return _list(db, user, MediaAttachment.relationship_event_id, event_id)

async def _upload(request: Request, *, pet_id: int, source: dict[str, int], filename: str, content_type: str, duration_header: str | None, db: Session, user: User) -> MediaAttachment:
    normalized = content_type.split(";", 1)[0].strip().lower()
    if normalized not in ALLOWED_TYPES:
        raise APIError(415, "MEDIA_TYPE_NOT_ALLOWED", "Unsupported media type")
    duration_seconds = None
    if normalized.startswith("video/"):
        if not duration_header or not duration_header.isdigit():
            raise APIError(422, "MEDIA_DURATION_REQUIRED", "Video duration is required")
        duration_seconds = int(duration_header)
        if duration_seconds < 1 or duration_seconds > settings.media_max_video_seconds:
            raise APIError(413, "MEDIA_DURATION_INVALID", "Video duration exceeds the configured limit")
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > settings.media_max_bytes:
        raise APIError(413, "MEDIA_SIZE_INVALID", "Media must be non-empty and within the configured size limit")
    decoded_filename = unquote(filename)
    if any(character in decoded_filename for character in "\r\n"):
        raise APIError(422, "MEDIA_FILENAME_INVALID", "Media filename is invalid")
    safe_name = Path(decoded_filename).name[:255]
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
        used = db.scalar(select(func.coalesce(func.sum(MediaAttachment.byte_size), 0)).join(Pet, MediaAttachment.pet_id == Pet.id).where(Pet.owner_user_id == user.id)) or 0
        if used + size > settings.media_total_bytes_per_user:
            raise APIError(413, "MEDIA_CAPACITY_EXCEEDED", "Account media capacity would be exceeded")
        temporary.replace(path)
        item = MediaAttachment(pet_id=pet_id, **source, original_filename=safe_name, media_type=normalized, byte_size=size, sha256=digest.hexdigest(), storage_key=storage_key, duration_seconds=duration_seconds, ai_candidate_status="NONE")
        db.add(item); db.flush(); _append_revision(db, item, "上传附件"); db.commit()
    except Exception:
        db.rollback()
        if temporary.is_file(): temporary.unlink()
        if path.is_file(): path.unlink()
        raise
    db.refresh(item)
    return item

@router.post("/episodes/{episode_id}/media", response_model=MediaAttachmentRead, status_code=201)
async def upload_media(request: Request, episode_id: int, filename: str = Header(alias="X-Filename"), content_type: str = Header(alias="Content-Type"), duration: str | None = Header(default=None, alias="X-Media-Duration-Seconds"), db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    episode = require_episode(db, episode_id, user, for_update=True)
    return await _upload(request, pet_id=episode.pet_id, source={"episode_id": episode_id}, filename=filename, content_type=content_type, duration_header=duration, db=db, user=user)

@router.post("/life-events/{event_id}/media", response_model=MediaAttachmentRead, status_code=201)
async def upload_life_event_media(request: Request, event_id: int, filename: str = Header(alias="X-Filename"), content_type: str = Header(alias="Content-Type"), duration: str | None = Header(default=None, alias="X-Media-Duration-Seconds"), db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    event = require_life_event(db, event_id, user, for_update=True)
    return await _upload(request, pet_id=event.pet_id, source={"life_event_id": event_id}, filename=filename, content_type=content_type, duration_header=duration, db=db, user=user)

@router.post("/relationship-events/{event_id}/media", response_model=MediaAttachmentRead, status_code=201)
async def upload_relationship_event_media(request: Request, event_id: int, pet_id: int = Header(alias="X-Pet-ID"), filename: str = Header(alias="X-Filename"), content_type: str = Header(alias="Content-Type"), duration: str | None = Header(default=None, alias="X-Media-Duration-Seconds"), db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    event = get_relationship_event(db, event_id, user, for_update=True)
    if event is None: raise APIError(404, "RELATIONSHIP_EVENT_NOT_FOUND", "Relationship event not found")
    if pet_id not in {part.pet_id for part in event.participants}: raise APIError(404, "PET_NOT_FOUND", "Pet not found")
    return await _upload(request, pet_id=pet_id, source={"relationship_event_id": event_id}, filename=filename, content_type=content_type, duration_header=duration, db=db, user=user)

@router.patch("/media/{attachment_id}", response_model=MediaAttachmentRead)
def update_media(attachment_id: int, payload: MediaFactsUpdate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    item = _attachment(db, attachment_id, user)
    item.observable_facts = payload.observable_facts.strip() if payload.observable_facts and payload.observable_facts.strip() else None
    item.owner_caption = item.observable_facts; item.updated_at = datetime.now(timezone.utc); _append_revision(db, item, "更新主人说明")
    db.commit(); return _attachment(db, item.id, user)

@router.patch("/media/{attachment_id}/metadata", response_model=MediaAttachmentRead)
def update_media_metadata(attachment_id: int, payload: MediaMetadataUpdate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    item = _attachment(db, attachment_id, user)
    item.captured_at = payload.captured_at
    item.owner_caption = payload.owner_caption.strip() if payload.owner_caption and payload.owner_caption.strip() else None
    item.observable_facts = item.owner_caption
    item.updated_at = datetime.now(timezone.utc); _append_revision(db, item, payload.change_summary or "更新媒体说明")
    db.commit(); return _attachment(db, item.id, user)

@router.patch("/media/{attachment_id}/candidate", response_model=MediaAttachmentRead)
def update_media_candidate(attachment_id: int, payload: MediaCandidateUpdate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    item = _attachment(db, attachment_id, user)
    if payload.action == "CONFIRM":
        if item.ai_candidate_status != "PENDING": raise APIError(409, "MEDIA_CANDIDATE_NOT_PENDING", "Only a pending candidate can be confirmed")
        item.ai_candidate_status = "CONFIRMED"
    elif payload.action == "REJECT":
        if item.ai_candidate_status != "PENDING": raise APIError(409, "MEDIA_CANDIDATE_NOT_PENDING", "Only a pending candidate can be rejected")
        item.ai_candidate_status = "REJECTED"
    elif payload.action == "WITHDRAW": item.ai_candidate_status = "WITHDRAWN"
    item.updated_at = datetime.now(timezone.utc); _append_revision(db, item, payload.change_summary or f"候选操作：{payload.action}")
    db.commit(); return _attachment(db, item.id, user)

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
    return FileResponse(path, media_type=item.media_type, filename=item.original_filename, content_disposition_type="inline", headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})

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
