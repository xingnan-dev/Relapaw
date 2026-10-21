from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import require_csrf, require_current_user
from app.api.errors import APIError
from app.db.session import get_db
from app.models import OwnerProfile, User
from app.schemas.owner import OwnerProfileRead, OwnerProfileUpsert

router = APIRouter(prefix="/owner-profile", tags=["owner-profile"])


@router.put("", response_model=OwnerProfileRead)
def upsert_owner_profile(payload: OwnerProfileUpsert, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    profile = db.scalar(select(OwnerProfile).where(OwnerProfile.user_id == user.id))
    if profile is None:
        profile = OwnerProfile(user_id=user.id, **payload.model_dump())
        db.add(profile)
    else:
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("", response_model=OwnerProfileRead)
def get_owner_profile(db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    profile = db.scalar(select(OwnerProfile).where(OwnerProfile.user_id == user.id))
    if profile is None:
        raise APIError(404, "OWNER_PROFILE_NOT_FOUND", "Owner profile not found")
    return profile
