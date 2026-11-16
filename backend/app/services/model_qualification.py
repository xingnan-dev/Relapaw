from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.domain.educational_knowledge import KNOWLEDGE_SET
from app.domain.model_qualification import MODEL_QUALIFICATIONS, repository_qualification_matches
from app.models import ModelQualification


@dataclass(frozen=True)
class QualificationDecision:
    enabled: bool
    reason: str | None


def runtime_qualification_decision(db: Session, settings: Settings) -> QualificationDecision:
    if not settings.ai_enabled:
        return QualificationDecision(False, None)
    if settings.model_qualification != "QUALIFIED" or not settings.model_qualification_id:
        return QualificationDecision(False, "MODEL_NOT_QUALIFIED")
    base_url = settings.openai_base_url or "https://api.openai.com/v1"
    if not repository_qualification_matches(
        settings.model_qualification_id,
        provider=settings.model_provider,
        model=settings.openai_model or "",
        base_url=base_url,
        knowledge_set_version=KNOWLEDGE_SET["version"],
    ):
        return QualificationDecision(False, "MODEL_QUALIFICATION_DRIFT")
    expected = MODEL_QUALIFICATIONS[settings.model_qualification_id]
    try:
        stored = db.get(ModelQualification, settings.model_qualification_id)
    except SQLAlchemyError:
        return QualificationDecision(False, "MODEL_QUALIFICATION_RECORD_UNAVAILABLE")
    if stored is None:
        return QualificationDecision(False, "MODEL_QUALIFICATION_RECORD_MISSING")
    if stored.status != "APPROVED" or stored.revoked_at is not None:
        return QualificationDecision(False, "MODEL_QUALIFICATION_REVOKED")
    for field in (
        "manifest_version", "provider", "model", "endpoint_policy", "contracts",
        "knowledge_set_version", "evidence_manifest",
    ):
        if getattr(stored, field) != expected[field]:
            return QualificationDecision(False, "MODEL_QUALIFICATION_RECORD_MISMATCH")
    return QualificationDecision(True, None)


def revoke_qualification(db: Session, qualification_id: str, reason: str) -> ModelQualification:
    record = db.get(ModelQualification, qualification_id)
    if record is None:
        raise ValueError("Qualification record does not exist")
    normalized = reason.strip()
    if not normalized:
        raise ValueError("Revocation reason is required")
    if record.status != "REVOKED":
        now = datetime.now(timezone.utc)
        record.status = "REVOKED"
        record.revoked_at = now
        record.revocation_reason = normalized[:500]
        record.updated_at = now
        db.flush()
    return record
