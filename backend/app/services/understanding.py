from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.errors import APIError
from app.domain.enums import AnalysisRunStatus, ClaimStatus, SafetyStatus
from app.models import (
    AnalysisRun,
    Claim,
    ClaimEvidenceReference,
    Episode,
    EvidenceReference,
    Uncertainty,
    UserConfirmation,
)
from app.schemas.analysis import (
    AnalysisEvidenceInput,
    AnalysisRunCreate,
    ConfirmationCreate,
    UnderstandingInput,
    UnderstandingInterpretationInput,
    UnderstandingObservationInput,
    UnderstandingOutput,
)
from app.services.understanding_adapter import AdapterError, TextUnderstandingAdapter
from app.services.timeline import get_episode_detail


RUN_LOADS = (
    joinedload(AnalysisRun.episode),
    selectinload(AnalysisRun.claims).selectinload(Claim.evidence_references),
    selectinload(AnalysisRun.claims).selectinload(Claim.uncertainties),
    selectinload(AnalysisRun.claims).selectinload(Claim.confirmations),
)


@dataclass
class AnalysisExecutionError(Exception):
    code: str
    message: str
    status_code: int


def get_analysis_run(db: Session, run_id: int) -> AnalysisRun | None:
    return db.scalar(select(AnalysisRun).where(AnalysisRun.id == run_id).options(*RUN_LOADS))


def list_episode_analysis_runs(db: Session, episode_id: int) -> list[AnalysisRun]:
    return list(db.scalars(
        select(AnalysisRun)
        .where(AnalysisRun.episode_id == episode_id)
        .options(*RUN_LOADS)
        .order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc())
    ).unique().all())


def episode_has_analysis(db: Session, episode_id: int) -> bool:
    return db.scalar(select(AnalysisRun.id).where(AnalysisRun.episode_id == episode_id).limit(1)) is not None


def _excerpt_for(episode: Episode, source_type: str, source_id: int | None) -> str | None:
    if source_type == "RAW_OWNER_INPUT":
        return episode.raw_owner_input
    if source_type == "OBSERVATION":
        item = next((item for item in episode.observations if item.id == source_id), None)
        return item.description if item else None
    if source_type == "OWNER_INTERPRETATION":
        item = next((item for item in episode.owner_interpretations if item.id == source_id), None)
        return item.interpretation if item else None
    return None


def build_understanding_input(episode: Episode) -> UnderstandingInput:
    if episode.safety_check is None:
        raise APIError(409, "SAFETY_CHECK_REQUIRED", "A manual Safety Check is required before analysis")
    evidence = [AnalysisEvidenceInput(
        key=f"evidence:{item.id}",
        source_type=item.source_type,
        source_id=item.source_id,
        field_path=item.field_path,
        observed_at=item.observed_at,
        recorded_at=item.recorded_at,
        excerpt=_excerpt_for(episode, item.source_type, item.source_id),
    ) for item in episode.evidence_references]
    return UnderstandingInput(
        episode_id=episode.id,
        pet_id=episode.pet_id,
        raw_owner_input=episode.raw_owner_input,
        observations=[UnderstandingObservationInput(
            id=item.id,
            description=item.description,
            behavior_type=item.behavior_type,
            measured_value=item.measured_value,
            unit=item.unit,
        ) for item in episode.observations],
        owner_interpretations=[UnderstandingInterpretationInput(
            id=item.id, interpretation=item.interpretation
        ) for item in episode.owner_interpretations],
        safety_status=episode.safety_check.result,
        evidence=evidence,
    )


def _new_run(episode: Episode, payload: AnalysisRunCreate, adapter: TextUnderstandingAdapter, input_data: UnderstandingInput, status: str, *, output: UnderstandingOutput | None = None, error_code: str | None = None) -> AnalysisRun:
    descriptor = adapter.descriptor
    now = datetime.now(timezone.utc)
    return AnalysisRun(
        episode_id=episode.id,
        request_id=payload.request_id,
        status=status,
        adapter_name=descriptor.adapter_name,
        model_provider=descriptor.model_provider,
        model_name=descriptor.model_name,
        model_version=descriptor.model_version,
        prompt_contract_version=descriptor.prompt_contract_version,
        input_contract_version=descriptor.input_contract_version,
        output_contract_version=descriptor.output_contract_version,
        input_snapshot=input_data.model_dump(mode="json"),
        normalized_output=output.model_dump(mode="json") if output else None,
        error_code=error_code,
        source_episode_updated_at=episode.updated_at,
        completed_at=None if status == AnalysisRunStatus.RUNNING.value else now,
    )


def _lock_run_and_live_episode(db: Session, run_id: int, episode_id: int) -> tuple[AnalysisRun, Episode]:
    episode = db.scalar(
        select(Episode).where(Episode.id == episode_id, Episode.deleted_at.is_(None)).with_for_update()
    )
    if episode is None:
        db.rollback()
        raise AnalysisExecutionError(
            "ANALYSIS_SOURCE_DELETED",
            "The source Episode was deleted while analysis was running; no result was saved",
            409,
        )
    run = db.scalar(select(AnalysisRun).where(AnalysisRun.id == run_id).with_for_update())
    if run is None:
        db.rollback()
        raise AnalysisExecutionError(
            "ANALYSIS_SOURCE_DELETED",
            "The source Episode was deleted while analysis was running; no result was saved",
            409,
        )
    return run, episode


def _fail_run(run: AnalysisRun, code: str) -> None:
    run.status = AnalysisRunStatus.FAILED.value
    run.error_code = code
    run.completed_at = datetime.now(timezone.utc)


def execute_analysis(db: Session, episode_id: int, payload: AnalysisRunCreate, adapter: TextUnderstandingAdapter) -> AnalysisRun:
    existing = db.scalar(select(AnalysisRun).where(
        AnalysisRun.episode_id == episode_id,
        AnalysisRun.request_id == payload.request_id,
    ).options(*RUN_LOADS))
    if existing is not None:
        created_at = existing.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if (
            existing.status == AnalysisRunStatus.RUNNING.value
            and created_at <= datetime.now(timezone.utc) - timedelta(minutes=5)
        ):
            _fail_run(existing, "ANALYSIS_INTERRUPTED")
            db.flush()
        return existing

    db.scalar(
        select(Episode).where(Episode.id == episode_id, Episode.deleted_at.is_(None)).with_for_update()
    )
    episode = get_episode_detail(db, episode_id)
    if episode is None:
        raise APIError(404, "EPISODE_NOT_FOUND", "Episode not found")
    input_data = build_understanding_input(episode)
    if input_data.safety_status != SafetyStatus.NORMAL:
        run = _new_run(episode, payload, adapter, input_data, AnalysisRunStatus.BLOCKED_BY_SAFETY.value, error_code="ANALYSIS_BLOCKED_BY_SAFETY")
        db.add(run)
        db.flush()
        return get_analysis_run(db, run.id) or run

    # Persist an idempotency reservation before waiting on a remote provider.
    # A concurrent request with the same key observes RUNNING and cannot invoke
    # the provider a second time.
    run = _new_run(episode, payload, adapter, input_data, AnalysisRunStatus.RUNNING.value)
    db.add(run)
    try:
        db.flush()
        run_id = run.id
        db.commit()
    except IntegrityError:
        db.rollback()
        concurrent = db.scalar(select(AnalysisRun).where(
            AnalysisRun.episode_id == episode_id,
            AnalysisRun.request_id == payload.request_id,
        ).options(*RUN_LOADS))
        if concurrent is None:
            raise
        return concurrent
    try:
        output = UnderstandingOutput.model_validate(adapter.analyze(input_data))
    except AdapterError as exc:
        run, _episode = _lock_run_and_live_episode(db, run_id, episode_id)
        _fail_run(run, exc.code)
        db.flush()
        raise AnalysisExecutionError(exc.code, exc.message, exc.status_code)
    except ValidationError:
        run, _episode = _lock_run_and_live_episode(db, run_id, episode_id)
        _fail_run(run, "MODEL_OUTPUT_INVALID")
        db.flush()
        raise AnalysisExecutionError("MODEL_OUTPUT_INVALID", "Model output did not match the required contract", 502)

    evidence_by_key = {item.key: item for item in input_data.evidence}
    referenced_keys = {reference.evidence_key for claim in output.claims for reference in claim.evidence}
    if not referenced_keys.issubset(evidence_by_key):
        run, _episode = _lock_run_and_live_episode(db, run_id, episode_id)
        _fail_run(run, "MODEL_EVIDENCE_INVALID")
        db.flush()
        raise AnalysisExecutionError("MODEL_EVIDENCE_INVALID", "Model output referenced evidence outside the Episode", 502)

    run, episode = _lock_run_and_live_episode(db, run_id, episode_id)
    descriptor = adapter.descriptor
    run.status = AnalysisRunStatus.COMPLETED.value
    run.adapter_name = descriptor.adapter_name
    run.model_provider = descriptor.model_provider
    run.model_name = descriptor.model_name
    run.model_version = descriptor.model_version
    run.prompt_contract_version = descriptor.prompt_contract_version
    run.input_contract_version = descriptor.input_contract_version
    run.output_contract_version = descriptor.output_contract_version
    run.normalized_output = output.model_dump(mode="json")
    run.error_code = None
    run.completed_at = datetime.now(timezone.utc)
    source_rows = {f"evidence:{item.id}": item for item in episode.evidence_references}
    source_ids = [item.id for item in episode.evidence_references]
    db.refresh(episode, attribute_names=["updated_at"])
    current_updated_at = episode.updated_at
    source_updated_at = run.source_episode_updated_at
    if current_updated_at.tzinfo is None:
        current_updated_at = current_updated_at.replace(tzinfo=timezone.utc)
    if source_updated_at.tzinfo is None:
        source_updated_at = source_updated_at.replace(tzinfo=timezone.utc)
    source_changed = current_updated_at > source_updated_at
    live_evidence_ids = set(db.scalars(
        select(EvidenceReference.id).where(EvidenceReference.id.in_(source_ids))
    ).all()) if source_ids and not source_changed else set()
    for proposal in output.claims:
        claim = Claim(
            analysis_run_id=run.id,
            claim_type=proposal.claim_type,
            statement=proposal.statement,
            confidence_label=proposal.confidence_label.value,
            status=ClaimStatus.PROPOSED.value,
        )
        db.add(claim)
        db.flush()
        claim.evidence_references = [ClaimEvidenceReference(
            claim_id=claim.id,
            evidence_reference_id=(
                source_rows[item.evidence_key].id
                if source_rows[item.evidence_key].id in live_evidence_ids
                else None
            ),
            source_type=evidence_by_key[item.evidence_key].source_type,
            source_id=evidence_by_key[item.evidence_key].source_id,
            field_path=evidence_by_key[item.evidence_key].field_path,
            observed_at=evidence_by_key[item.evidence_key].observed_at,
            recorded_at=evidence_by_key[item.evidence_key].recorded_at,
            excerpt=evidence_by_key[item.evidence_key].excerpt,
            role=item.role.value,
        ) for item in proposal.evidence]
        claim.uncertainties = [Uncertainty(
            claim_id=claim.id, kind=item.kind.value, description=item.description
        ) for item in proposal.uncertainties]
    db.flush()
    db.expire(episode)
    return get_analysis_run(db, run.id) or run


def confirm_claim(db: Session, claim_id: int, payload: ConfirmationCreate) -> UserConfirmation:
    claim = db.scalar(select(Claim).where(Claim.id == claim_id).options(selectinload(Claim.confirmations)))
    if claim is None:
        raise APIError(404, "CLAIM_NOT_FOUND", "Claim not found")
    if claim.confirmations:
        raise APIError(409, "CLAIM_ALREADY_DECIDED", "Claim already has a final user decision")
    confirmation = UserConfirmation(claim_id=claim.id, decision=payload.decision.value, note=payload.note)
    claim.status = payload.decision.value
    db.add(confirmation)
    db.flush()
    return confirmation
