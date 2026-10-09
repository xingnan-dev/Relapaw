from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.domain.enums import EvidenceSourceType, SafetyStatus, VeterinaryEscalationStatus
from app.models import (
    Episode,
    EpisodePlanLink,
    EvidenceReference,
    Observation,
    ObservationPlan,
    OwnerInterpretation,
    SafetyCheck,
    VeterinaryEscalation,
)
from app.schemas.episode import CompleteEpisodeCreate, EpisodeUpdate
from app.services.timeline import get_episode_detail


def create_complete_episode(db: Session, payload: CompleteEpisodeCreate) -> Episode:
    plan = None
    if payload.plan_id is not None:
        plan = db.get(ObservationPlan, payload.plan_id)
        if plan is None:
            raise APIError(404, "OBSERVATION_PLAN_NOT_FOUND", "Observation plan not found")
        if plan.pet_id != payload.pet_id:
            raise APIError(409, "PLAN_PET_MISMATCH", "Observation plan belongs to another pet")

    episode_data = payload.model_dump(
        exclude={"observations", "owner_interpretations", "safety_check", "plan_id"}
    )
    episode = Episode(**episode_data)
    db.add(episode)
    db.flush()

    observations: list[Observation] = []
    for item in payload.observations:
        observation = Observation(episode_id=episode.id, **item.model_dump())
        db.add(observation)
        observations.append(observation)

    interpretations: list[OwnerInterpretation] = []
    for item in payload.owner_interpretations:
        interpretation = OwnerInterpretation(episode_id=episode.id, **item.model_dump())
        db.add(interpretation)
        interpretations.append(interpretation)

    db.flush()

    safety_data = payload.safety_check.model_dump()
    safety_data["result"] = payload.safety_check.result.value
    safety_data["danger_signals"] = [signal.value for signal in payload.safety_check.danger_signals]
    safety = SafetyCheck(episode_id=episode.id, **safety_data)
    db.add(safety)

    if payload.safety_check.result == SafetyStatus.ESCALATE_TO_VET:
        signal_text = ", ".join(signal.value for signal in payload.safety_check.danger_signals)
        reason = payload.safety_check.other_concern or f"Owner selected urgent concern: {signal_text}"
        db.add(
            VeterinaryEscalation(
                episode_id=episode.id,
                reason=reason,
                status=VeterinaryEscalationStatus.OPEN.value,
            )
        )

    plan_link = None
    if plan is not None:
        plan_link = EpisodePlanLink(episode_id=episode.id, plan_id=plan.id)
        db.add(plan_link)

    recorded_at = datetime.now(timezone.utc)
    evidence = [
        EvidenceReference(
            episode_id=episode.id,
            source_type=EvidenceSourceType.RAW_OWNER_INPUT.value,
            source_id=episode.id,
            field_path="raw_owner_input",
            observed_at=episode.happened_at,
            recorded_at=recorded_at,
        )
    ]
    evidence.extend(
        EvidenceReference(
            episode_id=episode.id,
            source_type=EvidenceSourceType.OBSERVATION.value,
            source_id=item.id,
            field_path="description",
            observed_at=episode.happened_at,
            recorded_at=recorded_at,
        )
        for item in observations
    )
    evidence.extend(
        EvidenceReference(
            episode_id=episode.id,
            source_type=EvidenceSourceType.OWNER_INTERPRETATION.value,
            source_id=item.id,
            field_path="interpretation",
            observed_at=episode.happened_at,
            recorded_at=recorded_at,
        )
        for item in interpretations
    )
    db.add_all(evidence)
    db.flush()

    episode.observations = observations
    episode.owner_interpretations = interpretations
    episode.safety_check = safety
    episode.evidence_references = evidence
    episode.plan_links = [plan_link] if plan_link is not None else []
    return episode


def update_episode_aggregate(db: Session, episode: Episode, payload: EpisodeUpdate) -> Episode:
    for key, value in payload.model_dump(exclude={"observations", "owner_interpretations"}).items():
        setattr(episode, key, value)
    episode.updated_at = datetime.now(timezone.utc)

    episode.observations.clear()
    episode.owner_interpretations.clear()
    episode.evidence_references.clear()
    db.flush()

    observations = [Observation(episode_id=episode.id, **item.model_dump()) for item in payload.observations]
    interpretations = [OwnerInterpretation(episode_id=episode.id, **item.model_dump()) for item in payload.owner_interpretations]
    db.add_all([*observations, *interpretations])
    db.flush()

    recorded_at = datetime.now(timezone.utc)
    evidence = [EvidenceReference(
        episode_id=episode.id,
        source_type=EvidenceSourceType.RAW_OWNER_INPUT.value,
        source_id=episode.id,
        field_path="raw_owner_input",
        observed_at=episode.happened_at,
        recorded_at=recorded_at,
    )]
    evidence.extend(EvidenceReference(
        episode_id=episode.id, source_type=EvidenceSourceType.OBSERVATION.value,
        source_id=item.id, field_path="description", observed_at=episode.happened_at,
        recorded_at=recorded_at,
    ) for item in observations)
    evidence.extend(EvidenceReference(
        episode_id=episode.id, source_type=EvidenceSourceType.OWNER_INTERPRETATION.value,
        source_id=item.id, field_path="interpretation", observed_at=episode.happened_at,
        recorded_at=recorded_at,
    ) for item in interpretations)
    db.add_all(evidence)
    db.flush()
    episode.observations = observations
    episode.owner_interpretations = interpretations
    episode.evidence_references = evidence
    return get_episode_detail(db, episode.id) or episode
