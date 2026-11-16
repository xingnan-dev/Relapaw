from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace

from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

from app.domain.educational_knowledge import KNOWLEDGE_SET
from app.domain.model_qualification import MODEL_QUALIFICATIONS, QUALIFICATION_ID
from app.models import ModelQualification
from app.services.model_qualification import revoke_qualification, runtime_qualification_decision


def configured_settings(**overrides):
    values = {
        "ai_enabled": True,
        "model_qualification": "QUALIFIED",
        "model_qualification_id": QUALIFICATION_ID,
        "model_provider": "qwen",
        "openai_model": "qwen3.7-plus-2026-05-26",
        "openai_base_url": "https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def install_record(db):
    manifest = MODEL_QUALIFICATIONS[QUALIFICATION_ID]
    record = ModelQualification(
        qualification_id=QUALIFICATION_ID,
        manifest_version=manifest["manifest_version"], status="APPROVED",
        provider=manifest["provider"], model=manifest["model"],
        endpoint_policy=deepcopy(manifest["endpoint_policy"]), contracts=deepcopy(manifest["contracts"]),
        knowledge_set_version=manifest["knowledge_set_version"], evidence_manifest=deepcopy(manifest["evidence_manifest"]),
        approved_at=datetime.fromisoformat(str(manifest["approved_at"]).replace("Z", "+00:00")),
    )
    db.add(record)
    db.flush()
    return record


def test_runtime_qualification_requires_exact_approved_database_record(client):
    with client.app.state.test_engine.begin() as connection:
        session_factory = sessionmaker(bind=connection)
        with session_factory() as db:
            assert runtime_qualification_decision(db, configured_settings()).reason == "MODEL_QUALIFICATION_RECORD_MISSING"
            install_record(db)
            assert runtime_qualification_decision(db, configured_settings()).enabled is True


def test_runtime_qualification_fails_closed_for_every_bound_dimension(client, monkeypatch):
    with client.app.state.test_engine.begin() as connection:
        session_factory = sessionmaker(bind=connection)
        with session_factory() as db:
            record = install_record(db)
            assert runtime_qualification_decision(db, configured_settings(model_provider="openai")).enabled is False
            assert runtime_qualification_decision(db, configured_settings(openai_model="moving-alias")).enabled is False
            assert runtime_qualification_decision(db, configured_settings(openai_base_url="https://workspace.cn-shanghai.maas.aliyuncs.com/compatible-mode/v1")).enabled is False
            record.contracts = []
            db.flush()
            assert runtime_qualification_decision(db, configured_settings()).reason == "MODEL_QUALIFICATION_RECORD_MISMATCH"
            record.contracts = deepcopy(MODEL_QUALIFICATIONS[QUALIFICATION_ID]["contracts"])
            record.knowledge_set_version = "stale-knowledge"
            db.flush()
            assert runtime_qualification_decision(db, configured_settings()).reason == "MODEL_QUALIFICATION_RECORD_MISMATCH"
            record.knowledge_set_version = KNOWLEDGE_SET["version"]
            record.evidence_manifest = []
            db.flush()
            assert runtime_qualification_decision(db, configured_settings()).reason == "MODEL_QUALIFICATION_RECORD_MISMATCH"


def test_revocation_is_auditable_and_immediately_blocks_runtime(client):
    with client.app.state.test_engine.begin() as connection:
        session_factory = sessionmaker(bind=connection)
        with session_factory() as db:
            record = install_record(db)
            revoke_qualification(db, QUALIFICATION_ID, "operator safety rollback")
            assert record.status == "REVOKED"
            assert record.revoked_at is not None
            assert record.revocation_reason == "operator safety rollback"
            assert runtime_qualification_decision(db, configured_settings()).reason == "MODEL_QUALIFICATION_REVOKED"


def test_ai_disabled_short_circuits_without_runtime_activation(client):
    with client.app.state.test_engine.begin() as connection:
        session_factory = sessionmaker(bind=connection)
        with session_factory() as db:
            decision = runtime_qualification_decision(db, configured_settings(ai_enabled=False))
            assert decision.enabled is False and decision.reason is None


def test_repository_evidence_hash_drift_fails_closed(client, monkeypatch):
    with client.app.state.test_engine.begin() as connection:
        session_factory = sessionmaker(bind=connection)
        with session_factory() as db:
            install_record(db)
            manifest = MODEL_QUALIFICATIONS[QUALIFICATION_ID]
            bad_evidence = deepcopy(manifest["evidence_manifest"])
            bad_evidence[0]["sha256"] = "0" * 64
            monkeypatch.setitem(manifest, "evidence_manifest", bad_evidence)
            decision = runtime_qualification_decision(db, configured_settings())
            assert decision.enabled is False
            assert decision.reason == "MODEL_QUALIFICATION_DRIFT"


def test_missing_qualification_table_fails_closed_without_raising():
    class UnavailableSession:
        def get(self, *_args, **_kwargs):
            raise OperationalError("SELECT", {}, Exception("missing table"))

    decision = runtime_qualification_decision(UnavailableSession(), configured_settings())
    assert decision.enabled is False
    assert decision.reason == "MODEL_QUALIFICATION_RECORD_UNAVAILABLE"
