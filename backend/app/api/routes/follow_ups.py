from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_episode, require_pet
from app.db.session import get_db
from app.domain.enums import FollowUpStatus
from app.schemas.episode import EpisodeRead
from app.schemas.follow_up import FollowUpComplete, FollowUpCreate, FollowUpListItem, FollowUpRead
from app.services.follow_ups import (
    cancel_follow_up,
    complete_follow_up,
    create_follow_up,
    list_pet_follow_ups,
    require_follow_up,
)

router = APIRouter(tags=["follow-ups"])


@router.post("/episodes/{episode_id}/follow-ups", response_model=FollowUpRead, status_code=201)
def schedule_follow_up(episode_id: int, payload: FollowUpCreate, db: Session = Depends(get_db)):
    episode = require_episode(db, episode_id)
    try:
        follow_up = create_follow_up(db, episode, payload.scheduled_at)
        db.commit()
        return follow_up
    except Exception:
        db.rollback()
        raise


@router.get("/pets/{pet_id}/follow-ups", response_model=list[FollowUpListItem])
def get_pet_follow_ups(
    pet_id: int,
    status: FollowUpStatus | None = None,
    timing: str | None = Query(default=None, pattern="^(ACTIONABLE|DUE|OVERDUE|UPCOMING)$"),
    timezone_offset_minutes: int = Query(default=0, ge=-840, le=840),
    db: Session = Depends(get_db),
):
    require_pet(db, pet_id)
    items = list_pet_follow_ups(db, pet_id, status, timing, timezone_offset_minutes)
    return [
        FollowUpListItem.model_validate({
            **item.__dict__,
            "source_episode_type": item.source_episode.episode_type,
            "source_raw_owner_input": item.source_episode.raw_owner_input,
            "source_happened_at": item.source_episode.happened_at,
            "timing_status": timing_state,
        })
        for item, timing_state in items
    ]


@router.post("/follow-ups/{follow_up_id}/complete", response_model=EpisodeRead)
def finish_follow_up(follow_up_id: int, payload: FollowUpComplete, db: Session = Depends(get_db)):
    follow_up = require_follow_up(db, follow_up_id)
    try:
        episode = complete_follow_up(db, follow_up, payload)
        db.commit()
        return episode
    except Exception:
        db.rollback()
        raise


@router.post("/follow-ups/{follow_up_id}/cancel", response_model=FollowUpRead)
def cancel_scheduled_follow_up(follow_up_id: int, db: Session = Depends(get_db)):
    follow_up = require_follow_up(db, follow_up_id)
    try:
        result = cancel_follow_up(follow_up)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
