from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Episode, Pet, RelationshipEvent, RelationshipInterpretation, RelationshipParticipant, RelationshipRevision, User
from app.schemas.relationship import RelationshipEventCreate, RelationshipEventUpdate


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
