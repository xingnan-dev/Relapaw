from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.errors import APIError
from app.domain.enums import EvidenceSourceType, FollowUpStatus
from app.models import Episode, EpisodeFollowUp, EvidenceReference
from app.schemas.episode import CompleteEpisodeCreate
from app.schemas.follow_up import FollowUpComplete
from app.services.records import create_complete_episode
from app.services.timeline import get_episode_detail


def require_follow_up(db: Session, follow_up_id: int) -> EpisodeFollowUp:
    follow_up = db.scalar(
        select(EpisodeFollowUp)
        .where(EpisodeFollowUp.id == follow_up_id)
        .options(joinedload(EpisodeFollowUp.source_episode))
    )
    if follow_up is None:
        raise APIError(404, "FOLLOW_UP_NOT_FOUND", "Follow-up not found")
    return follow_up


def create_follow_up(db: Session, episode: Episode, scheduled_at: datetime) -> EpisodeFollowUp:
    now = datetime.now(timezone.utc)
    if scheduled_at <= now:
        raise APIError(422, "INVALID_FOLLOW_UP_TIME", "scheduled_at must be in the future")
    follow_up = EpisodeFollowUp(
        source_episode_id=episode.id,
        scheduled_at=scheduled_at,
        status=FollowUpStatus.PENDING.value,
    )
    db.add(follow_up)
    db.flush()
    return follow_up


def timing_status(scheduled_at: datetime, now: datetime, timezone_offset_minutes: int) -> str:
    comparable = scheduled_at.replace(tzinfo=timezone.utc) if scheduled_at.tzinfo is None else scheduled_at.astimezone(timezone.utc)
    local_now = now - timedelta(minutes=timezone_offset_minutes)
    local_midnight_utc = local_now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=timezone_offset_minutes)
    if comparable < local_midnight_utc:
        return "OVERDUE"
    if comparable <= now:
        return "DUE"
    return "UPCOMING"


def list_pet_follow_ups(
    db: Session,
    pet_id: int,
    status: FollowUpStatus | None,
    timing: str | None,
    timezone_offset_minutes: int,
) -> list[tuple[EpisodeFollowUp, str]]:
    filters = [Episode.pet_id == pet_id, Episode.deleted_at.is_(None)]
    if status is not None:
        filters.append(EpisodeFollowUp.status == status.value)
    statement = (
        select(EpisodeFollowUp)
        .join(Episode, EpisodeFollowUp.source_episode_id == Episode.id)
        .where(*filters)
        .options(joinedload(EpisodeFollowUp.source_episode))
        .order_by(EpisodeFollowUp.scheduled_at, EpisodeFollowUp.id)
    )
    now = datetime.now(timezone.utc)
    items = [(item, timing_status(item.scheduled_at, now, timezone_offset_minutes)) for item in db.scalars(statement).all()]
    if timing == "ACTIONABLE":
        return [(item, state) for item, state in items if state in {"DUE", "OVERDUE"}]
    if timing in {"DUE", "OVERDUE", "UPCOMING"}:
        return [(item, state) for item, state in items if state == timing]
    return items


def complete_follow_up(db: Session, follow_up: EpisodeFollowUp, payload: FollowUpComplete) -> Episode:
    if follow_up.status == FollowUpStatus.COMPLETED.value:
        raise APIError(409, "FOLLOW_UP_ALREADY_COMPLETED", "Follow-up is already completed")
    if follow_up.status == FollowUpStatus.CANCELLED.value:
        raise APIError(409, "FOLLOW_UP_CANCELLED", "Cancelled follow-up cannot be completed")

    episode_payload = CompleteEpisodeCreate(
        pet_id=follow_up.source_episode.pet_id,
        **payload.model_dump(exclude={"outcome"}),
    )
    result = create_complete_episode(db, episode_payload)
    now = datetime.now(timezone.utc)
    follow_up_evidence = EvidenceReference(
        episode_id=result.id,
        source_type=EvidenceSourceType.FOLLOW_UP.value,
        source_id=follow_up.id,
        field_path="source_episode_id",
        observed_at=result.happened_at,
        recorded_at=now,
    )
    db.add(follow_up_evidence)
    result.evidence_references.append(follow_up_evidence)
    follow_up.result_episode_id = result.id
    follow_up.result_episode = result
    follow_up.status = FollowUpStatus.COMPLETED.value
    follow_up.outcome = payload.outcome.value
    follow_up.completed_at = now
    db.flush()
    return get_episode_detail(db, result.id) or result


def cancel_follow_up(follow_up: EpisodeFollowUp) -> EpisodeFollowUp:
    if follow_up.status == FollowUpStatus.COMPLETED.value:
        raise APIError(409, "FOLLOW_UP_ALREADY_COMPLETED", "Completed follow-up cannot be cancelled")
    if follow_up.status == FollowUpStatus.CANCELLED.value:
        raise APIError(409, "FOLLOW_UP_CANCELLED", "Follow-up is already cancelled")
    follow_up.status = FollowUpStatus.CANCELLED.value
    return follow_up


def episode_has_follow_ups(db: Session, episode_id: int) -> bool:
    return db.scalar(select(EpisodeFollowUp.id).where(or_(
        EpisodeFollowUp.source_episode_id == episode_id,
        EpisodeFollowUp.result_episode_id == episode_id,
    )).limit(1)) is not None
