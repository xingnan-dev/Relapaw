from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_current_user, require_csrf, require_pet
from app.db.session import get_db
from app.models import Pet, User
from app.api.errors import APIError
from app.schemas.episode import TimelinePage
from app.schemas.pet import PetCreate, PetRead, PetUpdate
from app.services.timeline import get_pet_timeline
from app.schemas.time import require_aware_utc
from datetime import datetime

router = APIRouter(prefix="/pets", tags=["pets"])


@router.post("", response_model=PetRead, status_code=201)
def create_pet(payload: PetCreate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    pet = Pet(owner_user_id=user.id, **payload.model_dump())
    db.add(pet)
    db.commit()
    db.refresh(pet)
    return pet


@router.get("", response_model=list[PetRead])
def list_pets(db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    return list(db.scalars(select(Pet).where(Pet.owner_user_id == user.id).order_by(Pet.created_at, Pet.id)).all())


@router.get("/{pet_id}", response_model=PetRead)
def get_pet(pet_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    return require_pet(db, pet_id, user)


@router.patch("/{pet_id}", response_model=PetRead)
def update_pet(pet_id: int, payload: PetUpdate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    pet = require_pet(db, pet_id, user, for_update=True)
    data = payload.model_dump(exclude_unset=True)
    effective_birth_date = data.get("birth_date", pet.birth_date)
    effective_approximate_age = data.get("approximate_age", pet.approximate_age)
    if effective_birth_date and effective_approximate_age:
        raise APIError(422, "INVALID_PET_AGE", "Provide birth_date or approximate_age, not both")
    for key, value in data.items():
        setattr(pet, key, value)
    db.commit()
    db.refresh(pet)
    return pet


@router.get("/{pet_id}/timeline", response_model=TimelinePage)
def pet_timeline(
    pet_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    from_at: datetime | None = Query(default=None, alias="from"),
    to_at: datetime | None = Query(default=None, alias="to"),
    episode_type: str | None = Query(default=None, min_length=1, max_length=100),
    plan_id: int | None = Query(default=None, ge=1),
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
    items, total = get_pet_timeline(db, pet_id, page, page_size, from_at, to_at, episode_type, plan_id)
    return TimelinePage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=page * page_size < total,
    )
