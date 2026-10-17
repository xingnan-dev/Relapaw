import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.config import settings
from app.demo.dataset_v1 import DATASET_VERSION, EPISODES, RECORDED_MODEL_VERSION, SCHEMA_REVISION, SYNTHETIC_PET_NAME
from app.models import AnalysisRun, BaselineEvidence, BaselineSnapshot, Claim, Episode, EvidenceReference, Pet, SafetyCheck


@dataclass(frozen=True)
class VerificationResult:
    dataset_version: str
    checks: tuple[str, ...]


class DemoVerificationError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DemoVerificationError(message)


def verify_dataset(db: Session, manifest_path: Path) -> VerificationResult:
    _require(manifest_path.is_file(), "Demo manifest is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DemoVerificationError("Demo manifest is unreadable") from exc
    _require(manifest.get("dataset_version") == DATASET_VERSION, "Dataset version does not match")
    _require(manifest.get("schema_revision") == SCHEMA_REVISION, "Manifest schema revision does not match")
    _require(manifest.get("synthetic") is True, "Manifest is not marked synthetic")

    revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    _require(revision == SCHEMA_REVISION, "Database migration revision does not match")
    _require((db.scalar(select(func.count()).select_from(Pet)) or 0) == 1, "Expected exactly one synthetic pet")
    pet = db.scalar(select(Pet).where(Pet.name == SYNTHETIC_PET_NAME))
    _require(pet is not None, "Synthetic pet is missing")
    episode_count = db.scalar(select(func.count()).select_from(Episode).where(Episode.pet_id == pet.id)) or 0
    _require(episode_count == len(EPISODES), "Synthetic episode count does not match")
    _require((db.scalar(select(func.count()).select_from(SafetyCheck)) or 0) == len(EPISODES), "Safety coverage is incomplete")
    evidence_count = db.scalar(select(func.count()).select_from(EvidenceReference)) or 0
    _require(evidence_count == len(EPISODES) * 3, "Episode evidence references are incomplete")
    completed = db.scalar(select(AnalysisRun).where(
        AnalysisRun.status == "COMPLETED", AnalysisRun.model_version == RECORDED_MODEL_VERSION
    ))
    _require(completed is not None, "Recorded analysis is missing")
    _require((db.scalar(select(func.count()).select_from(Claim).where(Claim.analysis_run_id == completed.id)) or 0) == 1, "Recorded claim is missing")
    snapshot = db.scalar(select(BaselineSnapshot).where(BaselineSnapshot.pet_id == pet.id, BaselineSnapshot.window == "7d"))
    _require(snapshot is not None and snapshot.status == "READY", "Ready 7-day baseline is missing")
    lineage = db.scalar(select(func.count()).select_from(BaselineEvidence).where(BaselineEvidence.snapshot_id == snapshot.id)) or 0
    _require(lineage > 0, "Baseline lineage is missing")
    return VerificationResult(DATASET_VERSION, ("manifest", "migration", "pet", "episodes", "safety", "evidence", "recorded-analysis", "baseline"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the Relapaw synthetic demo dataset")
    parser.parse_args()
    demo_directory = Path(__file__).resolve().parents[2] / ".demo"
    expected_database = (demo_directory / "relapaw-demo.db").resolve()
    prefix = "sqlite:///"
    if settings.environment != "demo" or settings.ai_enabled:
        raise RuntimeError("Verify requires RELAPAW_ENV=demo and RELAPAW_AI_ENABLED=false")
    if not settings.database_url.startswith(prefix) or Path(settings.database_url[len(prefix):]).resolve() != expected_database:
        raise RuntimeError("Configured database is not backend/.demo/relapaw-demo.db")
    with SessionLocal() as db:
        result = verify_dataset(db, demo_directory / "manifest.json")
    print(json.dumps({"dataset_version": result.dataset_version, "checks": result.checks}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
