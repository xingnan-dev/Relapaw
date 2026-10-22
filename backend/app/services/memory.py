from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import MemoryDecisionType
from app.models.entities import AnalysisRun, Claim, MemoryCandidate, MemoryDecision, MemoryRevision
from app.schemas.memory import ManualMemoryCreate, ManualMemoryUpdate, MemoryDecisionCreate


class MemoryError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _candidate_options():
    return (
        selectinload(MemoryCandidate.decisions),
        selectinload(MemoryCandidate.revisions),
        selectinload(MemoryCandidate.claim)
        .selectinload(Claim.analysis_run)
        .selectinload(AnalysisRun.episode),
    )


def get_memory_candidate(db: Session, candidate_id: int, *, for_update: bool = False) -> MemoryCandidate | None:
    statement = (
        select(MemoryCandidate)
        .where(MemoryCandidate.id == candidate_id)
        .options(*_candidate_options())
        .execution_options(populate_existing=True)
    )
    if for_update:
        statement = statement.with_for_update()
    return db.scalar(statement)


def get_memory_candidate_by_claim(db: Session, claim_id: int) -> MemoryCandidate | None:
    return db.scalar(
        select(MemoryCandidate)
        .where(MemoryCandidate.claim_id == claim_id)
        .options(*_candidate_options())
        .execution_options(populate_existing=True)
    )


def list_memory_candidates(db: Session, pet_id: int) -> list[MemoryCandidate]:
    return list(
        db.scalars(
            select(MemoryCandidate)
            .where(MemoryCandidate.pet_id == pet_id)
            .options(*_candidate_options())
            .order_by(MemoryCandidate.id.desc())
            .execution_options(populate_existing=True)
        ).all()
    )


def list_long_term_memory(db: Session, pet_id: int) -> list[MemoryCandidate]:
    return [candidate for candidate in list_memory_candidates(db, pet_id) if candidate.state == "ACTIVE"]


def materialize_memory_candidate(db: Session, claim_id: int) -> MemoryCandidate:
    existing = get_memory_candidate_by_claim(db, claim_id)
    if existing is not None:
        return existing

    claim = db.scalar(
        select(Claim)
        .where(Claim.id == claim_id)
        .options(
            selectinload(Claim.confirmations),
            selectinload(Claim.evidence_references),
            selectinload(Claim.uncertainties),
            selectinload(Claim.analysis_run).selectinload(AnalysisRun.episode),
        )
    )
    if claim is None:
        raise MemoryError(404, "CLAIM_NOT_FOUND", "Claim not found")
    if claim.status != "CONFIRMED" or not claim.confirmations or claim.confirmations[-1].decision != "CONFIRMED":
        raise MemoryError(409, "CLAIM_NOT_CONFIRMED", "Only a confirmed claim can become a memory candidate")
    if claim.analysis_run.status != "COMPLETED":
        raise MemoryError(409, "ANALYSIS_NOT_COMPLETED", "The source analysis is not completed")
    if claim.analysis_run.is_stale:
        raise MemoryError(409, "CLAIM_STALE", "The source episode changed after this claim was generated")

    run = claim.analysis_run
    candidate = MemoryCandidate(
        pet_id=run.episode.pet_id,
        claim_id=claim.id,
        source_type="CLAIM",
        claim_snapshot={
            "claim_type": claim.claim_type,
            "statement": claim.statement,
            "confidence_label": claim.confidence_label,
        },
        evidence_snapshot=[
            {
                "source_type": evidence.source_type,
                "source_id": evidence.source_id,
                "field_path": evidence.field_path,
                "observed_at": evidence.observed_at.isoformat(),
                "recorded_at": evidence.recorded_at.isoformat(),
                "excerpt": evidence.excerpt,
                "role": evidence.role,
            }
            for evidence in claim.evidence_references
        ],
        uncertainty_snapshot=[
            {"kind": uncertainty.kind, "description": uncertainty.description}
            for uncertainty in claim.uncertainties
        ],
        model_snapshot={
            "adapter_name": run.adapter_name,
            "model_provider": run.model_provider,
            "model_name": run.model_name,
            "model_version": run.model_version,
            "prompt_contract_version": run.prompt_contract_version,
            "input_contract_version": run.input_contract_version,
            "output_contract_version": run.output_contract_version,
            "analysis_run_id": run.id,
        },
        source_episode_updated_at=run.source_episode_updated_at,
    )
    db.add(candidate)
    db.flush()
    return get_memory_candidate(db, candidate.id)  # type: ignore[return-value]


def update_manual_memory_candidate(db: Session, candidate_id: int, payload: ManualMemoryUpdate) -> MemoryCandidate:
    candidate = get_memory_candidate(db, candidate_id, for_update=True)
    if candidate is None:
        raise MemoryError(404, "MEMORY_CANDIDATE_NOT_FOUND", "Memory candidate not found")
    if candidate.source_type != "MANUAL":
        raise MemoryError(409, "MEMORY_SOURCE_READ_ONLY", "Claim-derived memory candidates cannot be edited")
    current_category = str(candidate.claim_snapshot.get("claim_type", "OTHER"))
    current_statement = str(candidate.claim_snapshot.get("statement", ""))
    if current_category == payload.category and current_statement == payload.statement:
        return candidate
    revision_number = max((item.revision_number for item in candidate.revisions), default=0) + 1
    candidate.claim_snapshot = {
        "claim_type": payload.category,
        "statement": payload.statement,
        "confidence_label": "USER_STATED",
    }
    db.add(MemoryRevision(candidate_id=candidate.id, revision_number=revision_number, category=payload.category, statement=payload.statement))
    db.flush()
    return get_memory_candidate(db, candidate.id)  # type: ignore[return-value]


def create_manual_memory_candidate(db: Session, pet_id: int, payload: ManualMemoryCreate) -> MemoryCandidate:
    candidate = MemoryCandidate(
        pet_id=pet_id,
        claim_id=None,
        source_type="MANUAL",
        claim_snapshot={
            "claim_type": payload.category,
            "statement": payload.statement,
            "confidence_label": "USER_STATED",
        },
        evidence_snapshot=[],
        uncertainty_snapshot=[],
        model_snapshot={"source": "manual", "model_provider": "none"},
        source_episode_updated_at=None,
    )
    db.add(candidate)
    db.flush()
    db.add(MemoryRevision(candidate_id=candidate.id, revision_number=1, category=payload.category, statement=payload.statement))
    db.flush()
    return get_memory_candidate(db, candidate.id)  # type: ignore[return-value]


def append_memory_decision(db: Session, candidate_id: int, payload: MemoryDecisionCreate) -> MemoryCandidate:
    candidate = get_memory_candidate(db, candidate_id, for_update=True)
    if candidate is None:
        raise MemoryError(404, "MEMORY_CANDIDATE_NOT_FOUND", "Memory candidate not found")

    previous_request = next((item for item in candidate.decisions if item.request_id == payload.request_id), None)
    if previous_request is not None:
        if previous_request.decision != payload.decision.value or previous_request.note != payload.note:
            raise MemoryError(409, "IDEMPOTENCY_CONFLICT", "The request_id was already used with a different payload")
        return candidate

    projected_state = (
        "ELIGIBLE"
        if not candidate.decisions
        else ("ACTIVE" if candidate.decisions[-1].decision == "INCLUDE" else "WITHDRAWN")
    )
    if candidate.is_stale and payload.decision == MemoryDecisionType.INCLUDE:
        raise MemoryError(409, "MEMORY_CANDIDATE_STALE", "A stale candidate cannot be included")

    current_state = projected_state
    if payload.decision == MemoryDecisionType.INCLUDE and current_state not in {"ELIGIBLE", "WITHDRAWN"}:
        raise MemoryError(409, "INVALID_MEMORY_TRANSITION", "Only an eligible or withdrawn candidate can be included")
    if payload.decision == MemoryDecisionType.WITHDRAW and current_state != "ACTIVE":
        raise MemoryError(409, "INVALID_MEMORY_TRANSITION", "Only an active candidate can be withdrawn")

    db.add(
        MemoryDecision(
            candidate_id=candidate.id,
            request_id=payload.request_id,
            decision=payload.decision.value,
            note=payload.note,
        )
    )
    db.flush()
    return get_memory_candidate(db, candidate.id)  # type: ignore[return-value]
