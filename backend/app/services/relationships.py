from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Episode, InteractionPatternCandidate, InteractionPatternDecisionRecord, InteractionPatternEvidence, InteractionPatternRevision, Pet, RelationshipEvent, RelationshipInterpretation, RelationshipParticipant, RelationshipRevision, User
from app.schemas.relationship import InteractionPatternCreate, InteractionPatternDecision, InteractionPatternUpdate, RelationshipEventCreate, RelationshipEventUpdate

PATTERN_GENERATOR_VERSION = "interaction-pattern/owner-reviewed-v1"


class RelationshipError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code, self.code, self.message = status_code, code, message


def _loads():
    return (
        selectinload(RelationshipEvent.participants),
        selectinload(RelationshipEvent.interpretations),
        selectinload(RelationshipEvent.revisions),
    )


def get_relationship_event(db: Session, event_id: int, user: User, *, for_update: bool = False) -> RelationshipEvent | None:
    statement = select(RelationshipEvent).where(
        RelationshipEvent.id == event_id,
        RelationshipEvent.owner_user_id == user.id,
        ~RelationshipEvent.participants.any(RelationshipParticipant.pet.has(Pet.archived_at.is_not(None))),
    ).options(*_loads()).execution_options(populate_existing=True)
    if for_update:
        statement = statement.with_for_update()
    return db.scalar(statement)


def list_relationship_events(db: Session, pet_id: int, user: User) -> list[RelationshipEvent]:
    return list(db.scalars(
        select(RelationshipEvent).join(RelationshipParticipant).join(Pet).where(
            RelationshipParticipant.pet_id == pet_id,
            RelationshipEvent.owner_user_id == user.id,
            Pet.owner_user_id == user.id,
            Pet.archived_at.is_(None),
            ~RelationshipEvent.participants.any(RelationshipParticipant.pet.has(Pet.archived_at.is_not(None))),
        ).options(*_loads()).order_by(RelationshipEvent.happened_at.desc(), RelationshipEvent.id.desc())
    ).unique().all())


def _validate_sources(db: Session, user: User, participant_ids: list[int], source_episode_id: int | None) -> None:
    pets = list(db.scalars(select(Pet).where(Pet.id.in_(participant_ids), Pet.owner_user_id == user.id, Pet.archived_at.is_(None))).all())
    if len(pets) != len(participant_ids):
        raise RelationshipError(404, "RELATIONSHIP_PARTICIPANT_NOT_FOUND", "A pet participant was not found")
    if source_episode_id is not None:
        episode = db.scalar(select(Episode).join(Pet).where(Episode.id == source_episode_id, Episode.deleted_at.is_(None), Pet.owner_user_id == user.id, Pet.archived_at.is_(None)))
        if episode is None or episode.pet_id not in participant_ids:
            raise RelationshipError(409, "RELATIONSHIP_SOURCE_MISMATCH", "Source episode must belong to an active participant pet")


def _append_revision(db: Session, event: RelationshipEvent, revision_number: int, participant_pet_ids: list[int], owner_interpretation: str | None) -> None:
    db.add(RelationshipRevision(
        event_id=event.id, revision_number=revision_number, relationship_kind=event.relationship_kind,
        happened_at=event.happened_at, participant_pet_ids=participant_pet_ids,
        observation_type=event.observation_type, observation_text=event.observation_text,
        owner_interpretation=owner_interpretation, source_episode_id=event.source_episode_id,
    ))


def create_relationship_event(db: Session, user: User, payload: RelationshipEventCreate) -> RelationshipEvent:
    _validate_sources(db, user, payload.participant_pet_ids, payload.source_episode_id)
    event = RelationshipEvent(owner_user_id=user.id, relationship_kind=payload.relationship_kind, happened_at=payload.happened_at, observation_type=payload.observation_type, observation_text=payload.observation_text, source_episode_id=payload.source_episode_id)
    db.add(event); db.flush()
    event.participants = [RelationshipParticipant(event_id=event.id, pet_id=pet_id) for pet_id in payload.participant_pet_ids]
    if payload.owner_interpretation is not None:
        event.interpretations.append(RelationshipInterpretation(event_id=event.id, interpretation=payload.owner_interpretation))
    _append_revision(db, event, 1, payload.participant_pet_ids, payload.owner_interpretation)
    db.flush()
    return get_relationship_event(db, event.id, user)  # type: ignore[return-value]


def update_relationship_event(db: Session, event_id: int, user: User, payload: RelationshipEventUpdate) -> RelationshipEvent:
    event = get_relationship_event(db, event_id, user, for_update=True)
    if event is None:
        raise RelationshipError(404, "RELATIONSHIP_EVENT_NOT_FOUND", "Relationship event not found")
    _validate_sources(db, user, payload.participant_pet_ids, payload.source_episode_id)
    event.relationship_kind = payload.relationship_kind
    event.happened_at = payload.happened_at
    event.observation_type = payload.observation_type
    event.observation_text = payload.observation_text
    event.source_episode_id = payload.source_episode_id
    event.updated_at = datetime.now(timezone.utc)
    event.participants.clear(); db.flush()
    event.participants = [RelationshipParticipant(event_id=event.id, pet_id=pet_id) for pet_id in payload.participant_pet_ids]
    if payload.owner_interpretation is not None and (not event.interpretations or event.interpretations[-1].interpretation != payload.owner_interpretation):
        event.interpretations.append(RelationshipInterpretation(event_id=event.id, interpretation=payload.owner_interpretation))
    _append_revision(db, event, max((item.revision_number for item in event.revisions), default=0) + 1, payload.participant_pet_ids, payload.owner_interpretation)
    db.flush()
    return get_relationship_event(db, event.id, user)  # type: ignore[return-value]


def _pattern_loads():
    return (
        selectinload(InteractionPatternCandidate.evidences),
        selectinload(InteractionPatternCandidate.revisions),
        selectinload(InteractionPatternCandidate.decisions),
    )


def get_interaction_pattern(db: Session, candidate_id: int, user: User, *, for_update: bool = False) -> InteractionPatternCandidate | None:
    statement = select(InteractionPatternCandidate).where(
        InteractionPatternCandidate.id == candidate_id,
        InteractionPatternCandidate.owner_user_id == user.id,
    ).options(*_pattern_loads()).execution_options(populate_existing=True)
    if for_update:
        statement = statement.with_for_update()
    candidate = db.scalar(statement)
    if candidate is None:
        return None
    active_pet_ids = set(db.scalars(select(Pet.id).where(
        Pet.owner_user_id == user.id, Pet.archived_at.is_(None), Pet.id.in_(candidate.participant_pet_ids),
    )).all())
    return candidate if active_pet_ids == set(candidate.participant_pet_ids) else None


def list_interaction_patterns(db: Session, pet_id: int, user: User) -> list[InteractionPatternCandidate]:
    owned = db.scalar(select(Pet.id).where(Pet.id == pet_id, Pet.owner_user_id == user.id, Pet.archived_at.is_(None)))
    if owned is None:
        raise RelationshipError(404, "PET_NOT_FOUND", "Pet not found")
    items = list(db.scalars(
        select(InteractionPatternCandidate).where(InteractionPatternCandidate.owner_user_id == user.id)
        .options(*_pattern_loads()).order_by(InteractionPatternCandidate.created_at.desc(), InteractionPatternCandidate.id.desc())
    ).all())
    active_pet_ids = set(db.scalars(select(Pet.id).where(Pet.owner_user_id == user.id, Pet.archived_at.is_(None))).all())
    return [item for item in items if pet_id in item.participant_pet_ids and set(item.participant_pet_ids) <= active_pet_ids]


def _append_pattern_revision(db: Session, candidate: InteractionPatternCandidate, change_summary: str | None = None) -> None:
    db.add(InteractionPatternRevision(
        candidate_id=candidate.id,
        revision_number=max((item.revision_number for item in candidate.revisions), default=0) + 1,
        title=candidate.title,
        observable_pattern=candidate.observable_pattern,
        counterevidence_summary=candidate.counterevidence_summary,
        confidence_limit=candidate.confidence_limit,
        change_summary=change_summary,
    ))


def create_interaction_pattern(db: Session, user: User, payload: InteractionPatternCreate) -> InteractionPatternCandidate:
    _validate_sources(db, user, payload.participant_pet_ids, None)
    roles = {event_id: "SUPPORTS" for event_id in payload.support_event_ids}
    roles.update({event_id: "CONTRADICTS" for event_id in payload.contradiction_event_ids})
    events = list(db.scalars(
        select(RelationshipEvent).where(
            RelationshipEvent.id.in_(roles), RelationshipEvent.owner_user_id == user.id,
        ).options(selectinload(RelationshipEvent.participants))
    ).all())
    if len(events) != len(roles):
        raise RelationshipError(404, "RELATIONSHIP_EVIDENCE_NOT_FOUND", "A relationship evidence record was not found")
    expected_participants = set(payload.participant_pet_ids)
    if any(event.relationship_kind != payload.relationship_kind or {item.pet_id for item in event.participants} != expected_participants for event in events):
        raise RelationshipError(409, "RELATIONSHIP_EVIDENCE_SCOPE_MISMATCH", "All evidence must describe the same relationship and participants")
    coverage_start = min(event.happened_at for event in events)
    coverage_end = max(event.happened_at for event in events)
    if (coverage_end - coverage_start).total_seconds() < 7 * 86400:
        raise RelationshipError(409, "INTERACTION_PATTERN_COVERAGE_TOO_SHORT", "Interaction pattern evidence must cover at least seven days")
    candidate = InteractionPatternCandidate(
        owner_user_id=user.id,
        relationship_kind=payload.relationship_kind,
        participant_pet_ids=payload.participant_pet_ids,
        initial_self_report=payload.initial_self_report,
        title=payload.title.strip(),
        observable_pattern=payload.observable_pattern.strip(),
        counterevidence_summary=payload.counterevidence_summary.strip(),
        evidence_count=len(events),
        coverage_start=coverage_start,
        coverage_end=coverage_end,
        generator_version=PATTERN_GENERATOR_VERSION,
        confidence_limit=payload.confidence_limit.strip(),
        status="ELIGIBLE",
        memory_status="NOT_INCLUDED",
    )
    db.add(candidate); db.flush()
    for event in sorted(events, key=lambda item: (item.happened_at, item.id)):
        db.add(InteractionPatternEvidence(
            candidate_id=candidate.id,
            relationship_event_id=event.id,
            role=roles[event.id],
            observation_type=event.observation_type,
            observation_snapshot=event.observation_text,
            happened_at=event.happened_at,
        ))
    _append_pattern_revision(db, candidate, "建立候选")
    db.flush()
    return get_interaction_pattern(db, candidate.id, user)  # type: ignore[return-value]


def update_interaction_pattern(db: Session, candidate_id: int, user: User, payload: InteractionPatternUpdate) -> InteractionPatternCandidate:
    candidate = get_interaction_pattern(db, candidate_id, user, for_update=True)
    if candidate is None:
        raise RelationshipError(404, "INTERACTION_PATTERN_NOT_FOUND", "Interaction pattern candidate not found")
    candidate.title = payload.title.strip()
    candidate.observable_pattern = payload.observable_pattern.strip()
    candidate.counterevidence_summary = payload.counterevidence_summary.strip()
    candidate.confidence_limit = payload.confidence_limit.strip()
    candidate.updated_at = datetime.now(timezone.utc)
    _append_pattern_revision(db, candidate, payload.change_summary)
    db.flush()
    return get_interaction_pattern(db, candidate.id, user)  # type: ignore[return-value]


def decide_interaction_pattern(db: Session, candidate_id: int, user: User, payload: InteractionPatternDecision) -> InteractionPatternCandidate:
    candidate = get_interaction_pattern(db, candidate_id, user, for_update=True)
    if candidate is None:
        raise RelationshipError(404, "INTERACTION_PATTERN_NOT_FOUND", "Interaction pattern candidate not found")
    previous_status = candidate.status
    previous_memory_status = candidate.memory_status
    if candidate.status == "WITHDRAWN" and payload.action != "WITHDRAW_FROM_MEMORY":
        raise RelationshipError(409, "INTERACTION_PATTERN_WITHDRAWN", "A withdrawn candidate cannot be changed")
    if payload.action == "CONFIRM":
        candidate.status = "CONFIRMED"
    elif payload.action == "REJECT":
        candidate.status = "REJECTED"; candidate.memory_status = "NOT_INCLUDED"
    elif payload.action == "WITHDRAW":
        candidate.status = "WITHDRAWN"; candidate.memory_status = "WITHDRAWN" if candidate.memory_status == "INCLUDED" else candidate.memory_status
    elif payload.action == "INCLUDE_IN_MEMORY":
        if candidate.status != "CONFIRMED":
            raise RelationshipError(409, "INTERACTION_PATTERN_CONFIRMATION_REQUIRED", "Confirm the candidate before including it in long-term memory")
        candidate.memory_status = "INCLUDED"
    else:
        candidate.memory_status = "WITHDRAWN"
    db.add(InteractionPatternDecisionRecord(
        candidate_id=candidate.id,
        action=payload.action,
        previous_status=previous_status,
        resulting_status=candidate.status,
        previous_memory_status=previous_memory_status,
        resulting_memory_status=candidate.memory_status,
        note=payload.note.strip() if payload.note else None,
    ))
    candidate.updated_at = datetime.now(timezone.utc)
    db.flush()
    return get_interaction_pattern(db, candidate.id, user)  # type: ignore[return-value]


def delete_interaction_pattern(db: Session, candidate_id: int, user: User) -> None:
    candidate = get_interaction_pattern(db, candidate_id, user, for_update=True)
    if candidate is None:
        raise RelationshipError(404, "INTERACTION_PATTERN_NOT_FOUND", "Interaction pattern candidate not found")
    db.delete(candidate)
    db.flush()
