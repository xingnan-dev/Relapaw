from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_episode, require_pet
from app.api.errors import APIError
from app.db.session import get_db
from app.models import Episode, Observation, OwnerInterpretation
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
from app.services.follow_ups import episode_has_follow_ups
from app.services.understanding import episode_has_analysis

router = APIRouter(prefix="/episodes", tags=["episodes"])


@router.get("/{episode_id}", response_model=EpisodeRead)
def get_episode(episode_id: int, db: Session = Depends(get_db)):
    episode = get_episode_detail(db, episode_id)
    if episode is None:
        raise APIError(404, "EPISODE_NOT_FOUND", "Episode not found")
    return episode


@router.put("/{episode_id}", response_model=EpisodeRead)
def update_episode(episode_id: int, payload: EpisodeUpdate, db: Session = Depends(get_db)):
    episode = require_episode(db, episode_id)
    try:
        updated = update_episode_aggregate(db, episode, payload)
        db.commit()
        return updated
    except Exception:
        db.rollback()
        raise


@router.delete("/{episode_id}", status_code=204)
def delete_episode(episode_id: int, db: Session = Depends(get_db)):
    episode = require_episode(db, episode_id)
    if episode_has_follow_ups(db, episode_id):
        raise APIError(409, "EPISODE_HAS_FOLLOW_UPS", "Episode has follow-up history and cannot be deleted")
    if episode_has_analysis(db, episode_id):
        raise APIError(409, "EPISODE_HAS_ANALYSIS", "Episode has analysis history and cannot be deleted")
    try:
        db.delete(episode)
        db.commit()
    except Exception:
        db.rollback()
        raise


@router.post("/complete", response_model=EpisodeRead, status_code=201)
def create_complete_episode_route(payload: CompleteEpisodeCreate, db: Session = Depends(get_db)):
    require_pet(db, payload.pet_id)
    try:
        episode = create_complete_episode(db, payload)
        db.commit()
        return episode
    except Exception:
        db.rollback()
        raise


@router.post("", response_model=EpisodeRead, status_code=201)
def create_episode(payload: EpisodeCreate, db: Session = Depends(get_db)):
    require_pet(db, payload.pet_id)
    episode = Episode(**payload.model_dump())
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return episode


@router.post("/{episode_id}/observations", response_model=ObservationRead, status_code=201)
def add_observation(episode_id: int, payload: ObservationCreate, db: Session = Depends(get_db)):
    require_episode(db, episode_id)
    observation = Observation(episode_id=episode_id, **payload.model_dump())
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation


@router.post("/{episode_id}/owner-interpretations", response_model=OwnerInterpretationRead, status_code=201)
def add_owner_interpretation(
    episode_id: int, payload: OwnerInterpretationCreate, db: Session = Depends(get_db)
):
    require_episode(db, episode_id)
    interpretation = OwnerInterpretation(episode_id=episode_id, **payload.model_dump())
    db.add(interpretation)
    db.commit()
    db.refresh(interpretation)
    return interpretation
