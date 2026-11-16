import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_current_user
from app.core.config import settings
from app.db.session import get_db
from app.schemas.capabilities import CapabilitiesRead
from app.demo.dataset_v1 import DATASET_VERSION, SCHEMA_REVISION
from app.services.model_qualification import QualificationDecision, runtime_qualification_decision


router = APIRouter(tags=["capabilities"])


def get_ai_decision(db: Session = Depends(get_db)) -> QualificationDecision:
    return runtime_qualification_decision(db, settings)


def get_ai_enabled(decision: QualificationDecision = Depends(get_ai_decision)) -> bool:
    return decision.enabled


def get_ai_block_reason(decision: QualificationDecision = Depends(get_ai_decision)) -> str | None:
    return decision.reason


def get_demo_dataset_version() -> str | None:
    manifest_path = Path(__file__).resolve().parents[3] / ".demo" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if (
        manifest.get("dataset_version") == DATASET_VERSION
        and manifest.get("schema_revision") == SCHEMA_REVISION
        and manifest.get("synthetic") is True
    ):
        return DATASET_VERSION
    return None


@router.get("/capabilities", response_model=CapabilitiesRead)
def read_capabilities(ai_enabled: bool = Depends(get_ai_enabled), _user=Depends(require_current_user)):
    is_demo = settings.environment == "demo"
    return CapabilitiesRead(
        environment=settings.environment,
        synthetic_data=is_demo,
        dataset_version=get_demo_dataset_version() if is_demo else None,
        ai_analysis_enabled=ai_enabled,
        model_qualification=settings.model_qualification,
        model_qualification_id=settings.model_qualification_id,
        medical_knowledge_version=settings.medical_knowledge_version,
        medical_review_status=settings.medical_review_status,
    )
