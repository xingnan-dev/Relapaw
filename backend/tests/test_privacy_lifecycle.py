from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import Base
from app.models import AnalysisRun, AuditEvent, Episode, EpisodeFollowUp, Pet, User, UserSession
from app.services.privacy import (
    build_account_export,
    purge_due_accounts,
    purge_expired_audit_events,
    redact_episode,
    request_account_deletion,
)


def privacy_db():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    return engine


def add_user_graph(db: Session, suffix: str = "1") -> tuple[User, Pet, Episode]:
    user = User(id=f"00000000-0000-0000-0000-00000000000{suffix}", status="ACTIVE")
    pet = Pet(owner=user, name=f"Pet {suffix}", species="cat")
    episode = Episode(
        pet=pet,
        happened_at=datetime.now(UTC),
        episode_type="behavior",
        raw_owner_input=f"private narrative {suffix}",
    )
    db.add(user)
    db.flush()
    return user, pet, episode


def test_export_is_tenant_scoped_and_omits_identity_subject_and_session_secrets():
    engine = privacy_db()
    with Session(engine) as db:
        user, pet, episode = add_user_graph(db, "1")
        other, _, _ = add_user_graph(db, "2")
        db.add(UserSession(
            user=user,
            token_hash="secret-token-hash",
            csrf_token_hash="secret-csrf-hash",
            created_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        ))
        db.commit()

        payload = build_account_export(db, user, settings)
        rendered = str(payload)
        assert payload["account"]["id"] == user.id
        assert [item["id"] for item in payload["pets"]] == [pet.id]
        assert [item["id"] for item in payload["episodes"]] == [episode.id]
        assert other.id not in rendered
        assert "secret-token-hash" not in rendered
        assert "secret-csrf-hash" not in rendered
    engine.dispose()


def test_export_keeps_completed_follow_up_lifecycle_after_source_redaction():
    engine = privacy_db()
    with Session(engine) as db:
        user, _, source = add_user_graph(db)
        result = Episode(
            pet=source.pet,
            happened_at=datetime.now(UTC),
            episode_type="follow-up",
            raw_owner_input="retained result",
        )
        db.add(result)
        db.flush()
        follow_up = EpisodeFollowUp(
            source_episode=source,
            result_episode=result,
            scheduled_at=datetime.now(UTC) - timedelta(days=1),
            status="COMPLETED",
            outcome="IMPROVED",
            completed_at=datetime.now(UTC),
        )
        db.add(follow_up)
        db.flush()
        follow_up_id = follow_up.id
        redact_episode(db, source, user, settings)
        db.commit()

        payload = build_account_export(db, user, settings)
        assert [item["id"] for item in payload["follow_ups"]] == [follow_up_id]
        assert [item["id"] for item in payload["episodes"]] == [result.id]
        assert "private narrative" not in str(payload)


def test_episode_redaction_removes_content_and_derived_analysis_but_keeps_audit():
    engine = privacy_db()
    with Session(engine) as db:
        user, _, episode = add_user_graph(db)
        db.flush()
        db.add(AnalysisRun(
            episode=episode,
            request_id="privacy-test",
            status="COMPLETED",
            adapter_name="deterministic",
            model_provider="none",
            model_name="none",
            model_version="v1",
            prompt_contract_version="v1",
            input_contract_version="v1",
            output_contract_version="v1",
            input_snapshot={"private": "derived"},
            normalized_output={"private": "derived"},
            source_episode_updated_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        ))
        db.flush()

        redact_episode(db, episode, user, settings)
        db.commit()

        db.refresh(episode)
        assert episode.deleted_at is not None
        assert episode.raw_owner_input == ""
        assert episode.context is None
        assert db.scalar(select(AnalysisRun.id)) is None
        audit = db.scalar(select(AuditEvent).where(AuditEvent.event_type == "EPISODE_CONTENT_DELETED"))
        assert audit is not None
        assert "private narrative" not in str(audit.metadata_json)
    engine.dispose()


def test_account_deletion_revokes_sessions_then_due_purge_preserves_audit():
    engine = privacy_db()
    with Session(engine) as db:
        user, _, source = add_user_graph(db, "1")
        other, _, _ = add_user_graph(db, "2")
        result = Episode(
            pet=source.pet,
            happened_at=datetime.now(UTC),
            episode_type="follow-up",
            raw_owner_input="result content",
        )
        db.add(result)
        db.flush()
        db.add(EpisodeFollowUp(
            source_episode=source,
            result_episode=result,
            scheduled_at=datetime.now(UTC) - timedelta(days=1),
            status="COMPLETED",
            outcome="IMPROVED",
            completed_at=datetime.now(UTC),
        ))
        session = UserSession(
            user=user,
            token_hash="token",
            csrf_token_hash="csrf",
            created_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        db.add(session)
        db.commit()

        due = request_account_deletion(db, user, settings)
        db.commit()
        db.refresh(session)
        assert user.status == "PENDING_DELETION"
        assert session.revoked_at is not None
        assert purge_due_accounts(db, settings, now=due - timedelta(seconds=1)) == 0
        assert purge_due_accounts(db, settings, now=due + timedelta(seconds=1)) == 1
        assert db.get(User, user.id) is None
        assert db.get(User, other.id) is not None
        assert db.scalar(select(AuditEvent.id).where(AuditEvent.event_type == "ACCOUNT_DATA_PURGED")) is not None
    engine.dispose()


def test_audit_retention_removes_only_expired_rows():
    engine = privacy_db()
    now = datetime.now(UTC)
    with Session(engine) as db:
        db.add_all([
            AuditEvent(id="old", actor_pseudonym="a", event_type="OLD", subject_type="USER", subject_pseudonym="s", metadata_json={}, created_at=now - timedelta(days=settings.audit_retention_days + 1)),
            AuditEvent(id="new", actor_pseudonym="a", event_type="NEW", subject_type="USER", subject_pseudonym="s", metadata_json={}, created_at=now),
        ])
        db.commit()
        assert purge_expired_audit_events(db, settings, now=now) == 1
        assert db.get(AuditEvent, "old") is None
        assert db.get(AuditEvent, "new") is not None
    engine.dispose()
