from datetime import datetime, timezone
from pathlib import Path
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.demo.dataset_v1 import DATASET_VERSION, EPISODES
from app.demo.seed import seed_dataset
from app.models import AnalysisRun, Episode, Pet, User


BASE_NOW = datetime(2026, 10, 17, 12, tzinfo=timezone.utc)


def test_seed_is_versioned_relative_and_idempotent(demo_db):
    sessions, manifest = demo_db
    with sessions() as db:
        assert seed_dataset(db, manifest, base_now=BASE_NOW) is True
    with sessions() as db:
        assert seed_dataset(db, manifest, base_now=BASE_NOW) is False
        assert db.scalar(select(func.count()).select_from(Pet)) == 1
        assert db.scalar(select(func.count()).select_from(Episode)) == len(EPISODES)
        assert db.scalar(select(func.count()).select_from(AnalysisRun)) == 1
        newest = db.scalar(select(Episode).order_by(Episode.happened_at.desc()))
        assert newest.happened_at.replace(tzinfo=timezone.utc) == BASE_NOW
    assert DATASET_VERSION in manifest.read_text(encoding="utf-8")


def test_seed_failure_rolls_back_everything_and_writes_no_manifest(demo_db):
    sessions, manifest = demo_db
    with sessions() as db:
        with pytest.raises(RuntimeError, match="forced seed failure"):
            seed_dataset(
                db,
                manifest,
                base_now=BASE_NOW,
                before_commit=lambda: (_ for _ in ()).throw(RuntimeError("forced seed failure")),
            )
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Pet)) == 0
    assert not manifest.exists()


def test_seed_refuses_nonempty_unknown_database(demo_db):
    sessions, manifest = demo_db
    with sessions() as db:
        owner = User(status="DISABLED")
        db.add(owner)
        db.flush()
        db.add(Pet(owner_user_id=owner.id, name="Real pet", species="dog"))
        db.commit()
        with pytest.raises(RuntimeError, match="not the expected demo dataset"):
            seed_dataset(db, manifest, base_now=BASE_NOW)


def test_fresh_alembic_database_can_be_seeded_and_verified(tmp_path, monkeypatch):
    database = tmp_path / "migrated-demo.db"
    database_url = f"sqlite:///{database.as_posix()}"
    monkeypatch.setattr(settings, "database_url", database_url)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    command.upgrade(config, "head")

    engine = create_engine(database_url)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    manifest = tmp_path / "manifest.json"
    with sessions() as db:
        assert seed_dataset(db, manifest, base_now=BASE_NOW) is True
        from app.demo.verify import verify_dataset

        assert verify_dataset(db, manifest).dataset_version == DATASET_VERSION
    engine.dispose()
