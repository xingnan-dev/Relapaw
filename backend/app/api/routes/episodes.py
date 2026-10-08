from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_episode, require_pet
from app.db.session import get_db
from app.models import Episode, Observation, OwnerInterpretation
from app.schemas.episode import (
    EpisodeCreate,
    EpisodeRead,
    ObservationCreate,
    ObservationRead,
    OwnerInterpretationCreate,
    OwnerInterpretationRead,
)

router = APIRouter(prefix="/episodes", tags=["episodes"])


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

