from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Episode, EpisodePlanLink, Observation, OwnerInterpretation


EPISODE_LOADS = (
    selectinload(Episode.observations),
    selectinload(Episode.owner_interpretations),
    selectinload(Episode.safety_check),
    selectinload(Episode.evidence_references),
    selectinload(Episode.plan_links),
    selectinload(Episode.veterinary_escalations),
    selectinload(Episode.scheduled_follow_ups),
    selectinload(Episode.result_of_follow_up),
)


def get_episode_detail(db: Session, episode_id: int) -> Episode | None:
    return db.scalar(
        select(Episode)
        .where(Episode.id == episode_id, Episode.deleted_at.is_(None))
        .options(*EPISODE_LOADS)
    )


def get_pet_timeline(
    db: Session,
    pet_id: int,
    page: int,
    page_size: int,
    from_at: datetime | None = None,
    to_at: datetime | None = None,
    episode_type: str | None = None,
    plan_id: int | None = None,
    query: str | None = None,
    category: str | None = None,
) -> tuple[list[Episode], int]:
    filters = [Episode.pet_id == pet_id, Episode.deleted_at.is_(None)]
    if from_at is not None:
        filters.append(Episode.happened_at >= from_at)
    if to_at is not None:
        filters.append(Episode.happened_at < to_at)
    if episode_type is not None:
        filters.append(Episode.episode_type == episode_type)
    if plan_id is not None:
        filters.append(Episode.plan_links.any(EpisodePlanLink.plan_id == plan_id))
    if query is not None:
        literal = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{literal}%"
        filters.append(or_(
            Episode.raw_owner_input.ilike(pattern, escape="\\"),
            Episode.location.ilike(pattern, escape="\\"),
            Episode.trigger_context.ilike(pattern, escape="\\"),
            Episode.observations.any(Observation.description.ilike(pattern, escape="\\")),
            Episode.owner_interpretations.any(OwnerInterpretation.interpretation.ilike(pattern, escape="\\")),
        ))
    if category is not None:
        filters.append(Episode.observations.any(Observation.standardized_category == category))
    total = db.scalar(select(func.count(Episode.id)).where(*filters)) or 0
    statement = (
        select(Episode)
        .where(*filters)
        .options(*EPISODE_LOADS)
        .order_by(Episode.happened_at.desc(), Episode.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(statement).all()), total
