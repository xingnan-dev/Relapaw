from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import require_csrf, require_current_user
from app.api.errors import APIError
from app.db.session import get_db
from app.models import OwnerProfile, User
from app.schemas.owner import OwnerProfileRead, OwnerProfileUpsert
from app.core.config import settings
from app.services.audit import append_audit_event

router = APIRouter(prefix="/owner-profile", tags=["owner-profile"])


@router.put("", response_model=OwnerProfileRead)
def upsert_owner_profile(payload: OwnerProfileUpsert, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    profile = db.scalar(select(OwnerProfile).where(OwnerProfile.user_id == user.id))
    previous_consent = profile.ai_context_enabled if profile is not None else False
    data = payload.model_dump()
    data["ai_context_fields"] = data["ai_context_fields"] if data["ai_context_enabled"] else None
    data["ai_context_consent_updated_at"] = datetime.now(UTC) if previous_consent != data["ai_context_enabled"] else (profile.ai_context_consent_updated_at if profile else None)
    if profile is None:
        profile = OwnerProfile(user_id=user.id, **data)
        db.add(profile)
    else:
        for key, value in data.items():
            setattr(profile, key, value)
    append_audit_event(db, settings, actor_user_id=user.id, event_type="OWNER_PROFILE_UPDATED", subject_type="OWNER_PROFILE", subject_id=profile.id or "pending", metadata={"ai_context_enabled": data["ai_context_enabled"], "ai_context_field_count": len(data["ai_context_fields"] or [])})
    db.commit()
    db.refresh(profile)
    return profile


@router.get("", response_model=OwnerProfileRead)
def get_owner_profile(db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    profile = db.scalar(select(OwnerProfile).where(OwnerProfile.user_id == user.id))
    if profile is None:
        raise APIError(404, "OWNER_PROFILE_NOT_FOUND", "Owner profile not found")
    return profile


@router.delete("", status_code=204)
def delete_owner_profile(db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    profile = db.scalar(select(OwnerProfile).where(OwnerProfile.user_id == user.id).with_for_update())
    if profile is not None:
        profile_id = profile.id
        db.delete(profile)
        append_audit_event(db, settings, actor_user_id=user.id, event_type="OWNER_PROFILE_DELETED", subject_type="OWNER_PROFILE", subject_id=profile_id, metadata={"ai_context_withdrawn": bool(profile.ai_context_enabled)})
        db.commit()
    return Response(status_code=204)
