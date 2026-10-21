from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_current_user, require_csrf, require_episode, require_pet, require_plan
from app.api.errors import APIError
from app.db.session import get_db
from app.domain.enums import EvidenceSourceType
from app.models import Episode, EvidenceReference, Observation, OwnerInterpretation, User
from app.schemas.episode import (
    CompleteEpisodeCreate,
    EpisodeCreate,
    EpisodeRead,
    EpisodeUpdate,
    ObservationCreate,
    ObservationRead,
    OwnerInterpretationCreate,
    OwnerInterpretationRead,
)
from app.services.records import create_complete_episode, update_episode_aggregate
from app.services.timeline import get_episode_detail
from app.core.config import settings
from app.services.privacy import redact_episode

router = APIRouter(prefix="/episodes", tags=["episodes"])


@router.get("/{episode_id}", response_model=EpisodeRead)
def get_episode(episode_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    require_episode(db, episode_id, user)
    episode = get_episode_detail(db, episode_id)
    if episode is None:
        raise APIError(404, "EPISODE_NOT_FOUND", "Episode not found")
    return episode


@router.put("/{episode_id}", response_model=EpisodeRead)
def update_episode(episode_id: int, payload: EpisodeUpdate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    episode = require_episode(db, episode_id, user, for_update=True)
    try:
        updated = update_episode_aggregate(db, episode, payload)
        db.commit()
        return updated
    except Exception:
        db.rollback()
        raise


@router.delete("/{episode_id}", status_code=204)
def delete_episode(episode_id: int, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    episode = require_episode(db, episode_id, user, for_update=True)
    try:
        redact_episode(db, episode, user, settings)
        db.commit()
    except Exception:
        db.rollback()
        raise


@router.post("/complete", response_model=EpisodeRead, status_code=201)
def create_complete_episode_route(payload: CompleteEpisodeCreate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    require_pet(db, payload.pet_id, user, for_update=True)
    if payload.plan_id is not None:
        require_plan(db, payload.plan_id, user)
    try:
        episode = create_complete_episode(db, payload)
        db.commit()
        return episode
    except Exception:
        db.rollback()
        raise


@router.post("", response_model=EpisodeRead, status_code=201)
def create_episode(payload: EpisodeCreate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    require_pet(db, payload.pet_id, user, for_update=True)
    episode = Episode(**payload.model_dump())
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return episode


@router.post("/{episode_id}/observations", response_model=ObservationRead, status_code=201)
def add_observation(episode_id: int, payload: ObservationCreate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)):
    episode = require_episode(db, episode_id, user, for_update=True)
    now = datetime.now(UTC)
    observation = Observation(episode_id=episode_id, **payload.model_dump())
    db.add(observation)
    db.flush()
    db.add(EvidenceReference(
        episode_id=episode_id,
        source_type=EvidenceSourceType.OBSERVATION.value,
        source_id=observation.id,
        field_path="description",
        observed_at=episode.happened_at,
        recorded_at=now,
    ))
    episode.updated_at = now
    db.commit()
    db.refresh(observation)
    return observation


@router.post("/{episode_id}/owner-interpretations", response_model=OwnerInterpretationRead, status_code=201)
def add_owner_interpretation(
    episode_id: int, payload: OwnerInterpretationCreate, db: Session = Depends(get_db), user: User = Depends(require_current_user), _csrf=Depends(require_csrf)
):
    episode = require_episode(db, episode_id, user, for_update=True)
    now = datetime.now(UTC)
    interpretation = OwnerInterpretation(episode_id=episode_id, **payload.model_dump())
    db.add(interpretation)
    db.flush()
    db.add(EvidenceReference(
        episode_id=episode_id,
        source_type=EvidenceSourceType.OWNER_INTERPRETATION.value,
        source_id=interpretation.id,
        field_path="interpretation",
        observed_at=episode.happened_at,
        recorded_at=now,
    ))
    episode.updated_at = now
    db.commit()
    db.refresh(interpretation)
    return interpretation
