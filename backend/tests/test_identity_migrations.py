from pathlib import Path

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
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261020_0014"
        owner_column = next(item for item in inspect(connection).get_columns("pets") if item["name"] == "owner_user_id")
        assert owner_column["nullable"] is False
        assert {"users", "user_identities", "identity_invitations", "user_sessions", "terms_acceptances", "audit_events"}.issubset(
            inspect(connection).get_table_names()
        )
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
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261020_0014"
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
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "20261020_0014"
    engine.dispose()
