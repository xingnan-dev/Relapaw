from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.models import Episode, Pet


def require_pet(db: Session, pet_id: int) -> Pet:
    pet = db.get(Pet, pet_id)
    if pet is None:
        raise APIError(404, "PET_NOT_FOUND", "Pet not found")
    return pet


def require_episode(db: Session, episode_id: int) -> Episode:
    episode = db.get(Episode, episode_id)
    if episode is None:
        raise APIError(404, "EPISODE_NOT_FOUND", "Episode not found")
    return episode
