import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.config import settings
from app.demo.dataset_v1 import (
    DATASET_VERSION,
    EPISODES,
    RECORDED_MODEL_VERSION,
    SCHEMA_REVISION,
    SYNTHETIC_PET_NAME,
    happened_at,
    normalized_base_now,
)
from app.models import (
    AnalysisRun,
    Claim,
    ClaimEvidenceReference,
    Episode,
    Pet,
    Uncertainty,
    User,
    UserConfirmation,
)
from app.schemas.episode import CompleteEpisodeCreate
from app.services.baseline import recompute_snapshot
from app.services.records import create_complete_episode


def manifest_payload(base_now: datetime) -> dict[str, object]:
    if base_now.tzinfo is None or base_now.utcoffset() is None:
        raise ValueError("base_now must include a timezone offset")
    return {
        "dataset_version": DATASET_VERSION,
        "schema_revision": SCHEMA_REVISION,
        "base_date": base_now.date().isoformat(),
        "synthetic": True,
    }


def write_manifest_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _recorded_analysis(db: Session, episode: Episode) -> None:
    evidence = episode.evidence_references
    run = AnalysisRun(
        episode_id=episode.id,
        request_id="demo-recorded-v1",
        status="COMPLETED",
        adapter_name="recorded-demo",
        model_provider="recorded-demo",
        model_name="synthetic-recording",
        model_version=RECORDED_MODEL_VERSION,
        prompt_contract_version="understanding-prompt/v1",
        input_contract_version="understanding-input/v1",
        output_contract_version="understanding-output/v1",
        input_snapshot={"source": "recorded-demo", "synthetic": True, "dataset_version": DATASET_VERSION},
        normalized_output={"source": "recorded-demo", "synthetic": True},
        source_episode_updated_at=episode.updated_at,
        completed_at=episode.happened_at,
    )
    db.add(run)
    db.flush()
    claim = Claim(
        analysis_run_id=run.id,
        claim_type="POSSIBLE_EXPLANATION",
        statement="联系兽医的决定可能源于主人注意到运动后呼吸模式偏离了 CanCan12 的通常表现。",
        confidence_label="MEDIUM",
        status="REJECTED",
    )
    db.add(claim)
    db.flush()
    for item, role, excerpt in (
        (evidence[0], "SUPPORTS", episode.raw_owner_input),
        (evidence[1], "SUPPORTS", episode.observations[0].description),
        (evidence[2], "SUPPORTS", episode.owner_interpretations[0].interpretation),
    ):
        db.add(ClaimEvidenceReference(
            claim_id=claim.id,
            evidence_reference_id=item.id,
            source_type=item.source_type,
            source_id=item.source_id,
            field_path=item.field_path,
            observed_at=item.observed_at,
            recorded_at=item.recorded_at,
            excerpt=excerpt,
            role=role,
        ))
    db.add_all([
        Uncertainty(claim_id=claim.id, kind="MISSING_CONTEXT", description="缺少正常呼吸频率和运动后恢复时间的客观基线。"),
        Uncertainty(claim_id=claim.id, kind="ALTERNATIVE_EXPLANATION", description="温度、湿度、牵引力度或兴奋程度也可能影响呼吸。"),
        UserConfirmation(claim_id=claim.id, decision="REJECTED", note="合成演示中的预置复核结果。"),
    ])


def seed_dataset(
    db: Session,
    manifest_path: Path,
    *,
    base_now: datetime,
    before_commit: Callable[[], None] | None = None,
) -> bool:
    """Seed an empty database, or return False when the exact dataset already exists."""
    base_now = normalized_base_now(base_now)
    existing_count = db.scalar(select(func.count()).select_from(Pet)) or 0
    if existing_count:
        pet = db.scalar(select(Pet).where(Pet.name == SYNTHETIC_PET_NAME))
        if pet is None or not manifest_path.is_file():
            raise RuntimeError("Database is not empty and is not the expected demo dataset")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("dataset_version") != DATASET_VERSION or manifest.get("synthetic") is not True:
            raise RuntimeError("Existing demo manifest does not match the expected dataset")
        from app.demo.verify import verify_dataset

        verify_dataset(db, manifest_path)
        return False

    try:
        demo_user = User(
            id="00000000-0000-0000-0000-00000000d3e0",
            status="DISABLED",
        )
        db.add(demo_user)
        db.flush()
        pet = Pet(
            owner_user_id=demo_user.id,
            name=SYNTHETIC_PET_NAME,
            species="dog",
            breed="synthetic mixed breed",
            approximate_age="4 years (synthetic)",
            sex="unknown",
            neutered=True,
        )
        db.add(pet)
        db.flush()
        seeded: list[Episode] = []
        for spec in EPISODES:
            occurred = happened_at(base_now, spec.days_ago)
            episode = create_complete_episode(db, CompleteEpisodeCreate.model_validate({
                "pet_id": pet.id,
                "happened_at": occurred,
                "episode_type": spec.episode_type,
                "raw_owner_input": spec.raw_owner_input,
                "duration_seconds": spec.duration_seconds,
                "frequency_count": 1,
                "intensity": spec.intensity,
                "location": "synthetic home",
                "context": {"synthetic": True, "dataset_version": DATASET_VERSION},
                "observations": [{
                    "behavior_type": spec.episode_type,
                    "description": spec.observation,
                    "source_type": "owner_direct",
                    "measured_value": spec.duration_seconds,
                    "unit": "seconds",
                }],
                "owner_interpretations": [{"interpretation": spec.interpretation}],
                "safety_check": {
                    "result": spec.safety_result,
                    "danger_signals": list(spec.danger_signals),
                    "acknowledged_at": occurred,
                },
            }))
            seeded.append(episode)
        _recorded_analysis(db, seeded[3])
        recompute_snapshot(db, pet.id, "7d", base_now)
        if before_commit is not None:
            before_commit()
        db.commit()
    except Exception:
        db.rollback()
        raise
    write_manifest_atomic(manifest_path, manifest_payload(base_now))
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the versioned Relapaw synthetic demo dataset")
    parser.add_argument("--base-now", type=datetime.fromisoformat, default=datetime.now(timezone.utc))
    args = parser.parse_args()
    demo_directory = Path(__file__).resolve().parents[2] / ".demo"
    expected_database = (demo_directory / "relapaw-demo.db").resolve()
    if settings.environment != "demo" or settings.ai_enabled:
        raise RuntimeError("Seed requires RELAPAW_ENV=demo and RELAPAW_AI_ENABLED=false")
    prefix = "sqlite:///"
    if not settings.database_url.startswith(prefix):
        raise RuntimeError("Seed only supports the fixed demo SQLite database")
    configured_database = Path(settings.database_url[len(prefix):]).resolve()
    if configured_database != expected_database:
        raise RuntimeError("Configured database is not backend/.demo/relapaw-demo.db")
    manifest = demo_directory / "manifest.json"
    with SessionLocal() as db:
        created = seed_dataset(db, manifest, base_now=args.base_now)
    print("seeded" if created else "already seeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
