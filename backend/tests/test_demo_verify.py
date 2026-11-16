import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete

from app.demo.dataset_v1 import DATASET_VERSION
from app.demo.seed import seed_dataset
from app.demo.verify import DemoVerificationError, verify_dataset
from app.models import EvidenceReference

BASE_NOW = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)


def test_verify_accepts_complete_dataset(demo_db):
    sessions, manifest = demo_db
    with sessions() as db:
        seed_dataset(db, manifest, base_now=BASE_NOW)
        result = verify_dataset(db, manifest)
    assert result.dataset_version == DATASET_VERSION
    assert "baseline" in result.checks


def test_verify_rejects_wrong_manifest_version(demo_db):
    sessions, manifest = demo_db
    with sessions() as db:
        seed_dataset(db, manifest, base_now=BASE_NOW)
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["dataset_version"] = "wrong/version"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(DemoVerificationError, match="Dataset version"):
            verify_dataset(db, manifest)


def test_verify_rejects_missing_key_relationship(demo_db):
    sessions, manifest = demo_db
    with sessions() as db:
        seed_dataset(db, manifest, base_now=BASE_NOW)
        db.execute(delete(EvidenceReference).where(EvidenceReference.id == 1))
        db.commit()
        with pytest.raises(DemoVerificationError, match="evidence references"):
            verify_dataset(db, manifest)


def test_verify_rejects_wrong_migration_revision(demo_db):
    sessions, manifest = demo_db
    with sessions() as db:
        seed_dataset(db, manifest, base_now=datetime(2026, 10, 17, tzinfo=timezone.utc))
        db.execute(__import__("sqlalchemy").text("UPDATE alembic_version SET version_num='old'"))
        db.commit()
        with pytest.raises(DemoVerificationError, match="migration revision"):
            verify_dataset(db, manifest)
