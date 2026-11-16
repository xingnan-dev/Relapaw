from hashlib import sha256
from pathlib import Path
from uuid import uuid4
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_current_user, require_csrf, require_pet
from app.db.session import get_db
from app.models import Pet, PetAvatar, User
from app.api.errors import APIError
from app.schemas.episode import TimelinePage
from app.schemas.pet import PetAvatarRead, PetCreate, PetRead, PetUpdate
from app.core.config import settings
from app.services.media_storage import cleanup_path
from app.services.timeline import get_pet_timeline
from app.schemas.time import require_aware_utc
from app.domain.enums import BehaviorCategory
from datetime import datetime, timezone

router = APIRouter(prefix="/pets", tags=["pets"])
AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _valid_avatar(media_type: str, head: bytes) -> bool:
    return (
        (media_type == "image/jpeg" and head.startswith(b"\xff\xd8\xff"))
        or (media_type == "image/png" and head.startswith(b"\x89PNG\r\n\x1a\n"))
        or (media_type == "image/webp" and head.startswith(b"RIFF") and head[8:12] == b"WEBP")
    )


@router.post("", response_model=PetRead, status_code=201)
def create_pet(payload: PetCreate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    pet = Pet(owner_user_id=user.id, **payload.model_dump())
    db.add(pet)
    db.commit()
    db.refresh(pet)
    return pet


@router.get("", response_model=list[PetRead])
def list_pets(include_archived: bool = False, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    query = select(Pet).where(Pet.owner_user_id == user.id)
    if not include_archived:
        query = query.where(Pet.archived_at.is_(None))
    return list(db.scalars(query.order_by(Pet.created_at, Pet.id)).all())


@router.get("/{pet_id}", response_model=PetRead)
def get_pet(pet_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    return require_pet(db, pet_id, user)


@router.patch("/{pet_id}", response_model=PetRead)
def update_pet(pet_id: int, payload: PetUpdate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    pet = require_pet(db, pet_id, user, for_update=True, allow_archived=True)
    data = payload.model_dump(exclude_unset=True)
    archived = data.pop("archived", None)
    effective_birth_date = data.get("birth_date", pet.birth_date)
    effective_approximate_age = data.get("approximate_age", pet.approximate_age)
    if effective_birth_date and effective_approximate_age:
        raise APIError(422, "INVALID_PET_AGE", "Provide birth_date or approximate_age, not both")
    for key, value in data.items():
        setattr(pet, key, value)
    if archived is not None:
        pet.archived_at = datetime.now(timezone.utc) if archived else None
    db.commit()
    db.refresh(pet)
    return pet


@router.put("/{pet_id}/avatar", response_model=PetAvatarRead)
async def replace_avatar(request: Request, pet_id: int, filename: str = Header(alias="X-Filename"), content_type: str = Header(alias="Content-Type"), db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    pet = require_pet(db, pet_id, user, for_update=True, allow_archived=True)
    normalized = content_type.split(";", 1)[0].strip().lower()
    if normalized not in AVATAR_TYPES:
        raise APIError(415, "AVATAR_TYPE_NOT_ALLOWED", "Avatar must be JPG, PNG, or WebP")
    decoded_filename = unquote(filename)
    if any(character in decoded_filename for character in "\r\n"):
        raise APIError(422, "AVATAR_FILENAME_INVALID", "Avatar filename is invalid")
    safe_name = Path(decoded_filename).name[:255]
    if not safe_name:
        raise APIError(422, "AVATAR_FILENAME_REQUIRED", "A filename is required")
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > settings.avatar_max_bytes:
        raise APIError(413, "AVATAR_SIZE_INVALID", "Avatar must be non-empty and within the configured size limit")
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    storage_key = f"avatar-{uuid4().hex}"
    path = settings.media_dir / storage_key
    temporary = settings.media_dir / f".{storage_key}.uploading"
    digest = sha256(); size = 0; head = b""
    try:
        with temporary.open("xb") as handle:
            async for chunk in request.stream():
                size += len(chunk)
                if size > settings.avatar_max_bytes:
                    raise APIError(413, "AVATAR_SIZE_INVALID", "Avatar must be non-empty and within the configured size limit")
                if len(head) < 32:
                    head += chunk[:32 - len(head)]
                digest.update(chunk); handle.write(chunk)
        if size == 0:
            raise APIError(413, "AVATAR_SIZE_INVALID", "Avatar must be non-empty and within the configured size limit")
        if not _valid_avatar(normalized, head):
            raise APIError(415, "AVATAR_CONTENT_MISMATCH", "File contents do not match the declared image type")
        temporary.replace(path)
        old_path = settings.media_dir / pet.avatar.storage_key if pet.avatar else None
        if pet.avatar is None:
            pet.avatar = PetAvatar(original_filename=safe_name, media_type=normalized, byte_size=size, sha256=digest.hexdigest(), storage_key=storage_key)
        else:
            pet.avatar.original_filename = safe_name; pet.avatar.media_type = normalized
            pet.avatar.byte_size = size; pet.avatar.sha256 = digest.hexdigest(); pet.avatar.storage_key = storage_key
            pet.avatar.updated_at = datetime.now(timezone.utc)
        db.commit(); db.refresh(pet.avatar)
    except Exception:
        db.rollback(); temporary.unlink(missing_ok=True); path.unlink(missing_ok=True); raise
    if old_path and old_path != path:
        cleanup_path(old_path, settings.media_dir)
    return pet.avatar


@router.get("/{pet_id}/avatar/content")
def get_avatar_content(pet_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    pet = require_pet(db, pet_id, user, allow_archived=True)
    if pet.avatar is None:
        raise APIError(404, "AVATAR_NOT_FOUND", "Pet avatar not found")
    path = settings.media_dir / pet.avatar.storage_key
    if not path.is_file():
        raise APIError(410, "AVATAR_FILE_MISSING", "Stored avatar file is missing")
    if sha256(path.read_bytes()).hexdigest() != pet.avatar.sha256:
        raise APIError(409, "AVATAR_FILE_CORRUPT", "Stored avatar failed integrity verification")
    return FileResponse(path, media_type=pet.avatar.media_type, filename=pet.avatar.original_filename, headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@router.delete("/{pet_id}/avatar", status_code=204)
def delete_avatar(pet_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    pet = require_pet(db, pet_id, user, for_update=True, allow_archived=True)
    if pet.avatar is None:
        return Response(status_code=204)
    path = settings.media_dir / pet.avatar.storage_key
    db.delete(pet.avatar); db.commit()
    cleanup_path(path, settings.media_dir)
    return Response(status_code=204)


@router.get("/{pet_id}/timeline", response_model=TimelinePage)
def pet_timeline(
    pet_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    from_at: datetime | None = Query(default=None, alias="from"),
    to_at: datetime | None = Query(default=None, alias="to"),
    episode_type: str | None = Query(default=None, min_length=1, max_length=100),
    plan_id: int | None = Query(default=None, ge=1),
    q: str | None = Query(default=None, min_length=1, max_length=200),
    category: BehaviorCategory | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_current_user),
):
    require_pet(db, pet_id, user)
    try:
        from_at = require_aware_utc(from_at)
        to_at = require_aware_utc(to_at)
    except ValueError as exc:
        raise APIError(422, "TIMEZONE_REQUIRED", str(exc)) from exc
    if from_at and to_at and to_at < from_at:
        raise APIError(422, "INVALID_TIMELINE_RANGE", "to must be on or after from")
    items, total = get_pet_timeline(db, pet_id, page, page_size, from_at, to_at, episode_type, plan_id, q, category.value if category else None)
    return TimelinePage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=page * page_size < total,
    )
