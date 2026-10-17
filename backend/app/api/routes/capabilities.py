import json
from pathlib import Path

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.schemas.capabilities import CapabilitiesRead
from app.demo.dataset_v1 import DATASET_VERSION, SCHEMA_REVISION


router = APIRouter(tags=["capabilities"])


def get_ai_enabled() -> bool:
    return settings.ai_enabled


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
def read_capabilities(ai_enabled: bool = Depends(get_ai_enabled)):
    is_demo = settings.environment == "demo"
    return CapabilitiesRead(
        environment=settings.environment,
        synthetic_data=is_demo,
        dataset_version=get_demo_dataset_version() if is_demo else None,
        ai_analysis_enabled=ai_enabled,
    )
