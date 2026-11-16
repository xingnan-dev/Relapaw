from pathlib import Path
import json

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.demo.assign_legacy_owner import LEGACY_DEMO_USER_ID, assign_legacy_demo_owner


def alembic_config(database_url: str) -> Config:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_empty_database_upgrades_to_identity_head(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}"
    monkeypatch.setattr(settings, "database_url", database_url)
    config = alembic_config(database_url)
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261026_0027"
        owner_column = next(item for item in inspect(connection).get_columns("pets") if item["name"] == "owner_user_id")
        assert owner_column["nullable"] is False
        assert {"users", "user_identities", "identity_invitations", "user_sessions", "terms_acceptances", "audit_events"}.issubset(
            inspect(connection).get_table_names()
        )
        qualification = connection.execute(text(
            "SELECT status, provider, model, knowledge_set_version, revoked_at FROM model_qualifications"
        )).mappings().one()
        assert qualification == {
            "status": "APPROVED", "provider": "qwen", "model": "qwen3.7-plus-2026-05-26",
            "knowledge_set_version": "controlled-education/2026-10-25-v1", "revoked_at": None,
        }
        command.downgrade(config, "20261026_0026")
        assert "model_qualifications" not in inspect(connection).get_table_names()
        command.upgrade(config, "20261026_0027")
        assert connection.scalar(text("SELECT status FROM model_qualifications")) == "APPROVED"
    engine.dispose()


def test_representative_legacy_database_requires_explicit_assignment(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}"
    monkeypatch.setattr(settings, "database_url", database_url)
    config = alembic_config(database_url)
    command.upgrade(config, "20261012_0008")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO pets (name, species) VALUES ('Synthetic legacy pet', 'dog')"
        ))

    command.upgrade(config, "20261020_0009")
    with Session(engine) as db:
        with pytest.raises(RuntimeError, match="Explicit"):
            assign_legacy_demo_owner(db, allowed=False)
        assert assign_legacy_demo_owner(db, allowed=True) == (1, 0)
        assert db.scalar(text("SELECT status FROM users WHERE id = :id"), {"id": LEGACY_DEMO_USER_ID}) == "DISABLED"

    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261026_0027"
        assert connection.scalar(text("SELECT count(*) FROM pets WHERE owner_user_id IS NULL")) == 0
        owner_column = next(item for item in inspect(connection).get_columns("pets") if item["name"] == "owner_user_id")
        assert owner_column["nullable"] is False
    engine.dispose()


def test_multiple_legacy_owner_profiles_receive_distinct_disabled_quarantine_users(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'legacy-profiles.db').as_posix()}"
    monkeypatch.setattr(settings, "database_url", database_url)
    config = alembic_config(database_url)
    command.upgrade(config, "20261012_0008")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO owner_profiles (interaction_preference) VALUES ('first'), ('second')"
        ))
    command.upgrade(config, "20261020_0009")
    with Session(engine) as db:
        assert assign_legacy_demo_owner(db, allowed=True) == (0, 2)
        owners = list(db.scalars(text("SELECT user_id FROM owner_profiles ORDER BY id")).all())
        assert len(owners) == len(set(owners)) == 2
        assert set(db.scalars(text(
            "SELECT status FROM users WHERE id IN (:first, :second)"
        ), {"first": owners[0], "second": owners[1]}).all()) == {"DISABLED"}
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261026_0027"
    engine.dispose()


def test_episode_revision_migration_backfills_existing_record_lenses(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'episode-revision.db').as_posix()}"
    monkeypatch.setattr(settings, "database_url", database_url)
    config = alembic_config(database_url)
    command.upgrade(config, "20261024_0021")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id, status) VALUES ('owner-1', 'ACTIVE')"))
        connection.execute(text("INSERT INTO pets (id, owner_user_id, name, species) VALUES (1, 'owner-1', 'Mochi', 'cat')"))
        connection.execute(text("INSERT INTO episodes (id, pet_id, happened_at, episode_type, raw_owner_input) VALUES (1, 1, '2026-10-01 08:00:00', 'daily_observation', '原来的话')"))
        connection.execute(text("INSERT INTO observations (episode_id, behavior_type, description, source_type) VALUES (1, 'resting', '蜷在毯子上', 'owner_direct')"))
        connection.execute(text("INSERT INTO owner_interpretations (episode_id, interpretation) VALUES (1, '我觉得它很放松')"))
        connection.execute(text("INSERT INTO safety_checks (episode_id, result, danger_signals, acknowledged_at) VALUES (1, 'NORMAL', '[]', '2026-10-01 08:05:00')"))

    command.upgrade(config, "head")
    with engine.connect() as connection:
        row = connection.execute(text("SELECT revision_number, source, snapshot FROM episode_revisions WHERE episode_id = 1")).mappings().one()
        snapshot = json.loads(row["snapshot"])
        assert row["revision_number"] == 1
        assert row["source"] == "MIGRATED_BASELINE"
        assert snapshot["raw_owner_input"] == "原来的话"
        assert snapshot["observations"][0]["description"] == "蜷在毯子上"
        assert snapshot["owner_interpretations"] == ["我觉得它很放松"]
        assert snapshot["safety_check"]["result"] == "NORMAL"
    engine.dispose()


def test_fact_extraction_migration_marks_existing_claims_as_legacy_and_round_trips(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'fact-extraction.db').as_posix()}"
    monkeypatch.setattr(settings, "database_url", database_url)
    config = alembic_config(database_url)
    command.upgrade(config, "20261025_0025")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO episodes (id, pet_id, happened_at, episode_type, raw_owner_input) "
            "VALUES (1, 1, '2026-10-01 08:00:00', 'note', 'legacy text')"
        ))
        connection.execute(text(
            "INSERT INTO analysis_runs "
            "(id, episode_id, request_id, status, adapter_name, model_provider, model_name, model_version, "
            "prompt_contract_version, input_contract_version, output_contract_version, input_snapshot, "
            "source_episode_updated_at) VALUES "
            "(1, 1, 'legacy', 'COMPLETED', 'legacy', 'legacy', 'legacy', 'v1', "
            "'legacy/v1', 'understanding-input/v1', 'understanding-output/v1', '{}', '2026-10-01 08:00:00')"
        ))
        connection.execute(text(
            "INSERT INTO claims (id, analysis_run_id, claim_type, statement, confidence_label, status) "
            "VALUES (1, 1, 'POSSIBLE_EXPLANATION', 'legacy claim', 'LOW', 'PROPOSED')"
        ))

    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT candidate_kind FROM claims WHERE id=1")) == "LEGACY_INTERPRETATION"
        assert next(item for item in inspect(connection).get_columns("claims") if item["name"] == "candidate_kind")["nullable"] is False

    command.downgrade(config, "20261025_0025")
    with engine.connect() as connection:
        assert "candidate_kind" not in {item["name"] for item in inspect(connection).get_columns("claims")}
        assert connection.scalar(text("SELECT statement FROM claims WHERE id=1")) == "legacy claim"
    engine.dispose()
