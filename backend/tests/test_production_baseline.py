import json
import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.demo.dataset_v1 import SCHEMA_REVISION


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def production_values(**overrides):
    values = {
        "RELAPAW_ENV": "production",
        "RELAPAW_DEPLOYMENT_VERSION": "release-test",
        "database_url": "postgresql+psycopg://relapaw:secret@db/relapaw",
        "cors_origins": ["https://beta.relapaw.example"],
        "RELAPAW_SESSION_PEPPER": "a-production-secret-that-is-not-the-default",
        "RELAPAW_TERMS_VERSION": "terms-v1",
        "RELAPAW_PRIVACY_VERSION": "privacy-v1",
        "RELAPAW_LEGAL_DOCUMENTS_APPROVED": True,
        "RELAPAW_MEDICAL_REVIEW_STATUS": "APPROVED",
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize("database_url", ["sqlite:///prod.db", "mysql://db/prod"])
def test_production_requires_postgresql(database_url):
    with pytest.raises(ValidationError, match="PostgreSQL"):
        Settings(_env_file=None, **production_values(database_url=database_url))


def test_compose_fixes_production_mode_and_requires_an_encoded_database_dsn():
    compose = (REPOSITORY_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "RELAPAW_ENV: production" in compose
    assert "RELAPAW_DATABASE_URL: ${RELAPAW_DATABASE_URL:" in compose
    assert "${RELAPAW_DB_PASSWORD}@" not in compose


def test_container_image_has_runtime_healthcheck_and_restrictive_build_context():
    dockerfile = (REPOSITORY_ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (REPOSITORY_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert "USER relapaw" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "http://127.0.0.1:8000/ready" in dockerfile
    for excluded in ("**/.env.*", "**/*.db", "**/*.sqlite", "**/*.log", "**/__pycache__"):
        assert excluded in dockerignore


@pytest.mark.parametrize("origins", [[], ["http://beta.example"], ["https://localhost:8443"]])
def test_production_requires_explicit_https_cors(origins):
    with pytest.raises(ValidationError, match="HTTPS origins"):
        Settings(_env_file=None, **production_values(cors_origins=origins))


def test_request_log_is_structured_and_does_not_log_query_or_body(client, caplog):
    secret = "must-never-appear-in-log"
    with caplog.at_level(logging.INFO, logger="relapaw.request"):
        response = client.post(f"/api/v1/auth/otp/request?secret={secret}", json={"email": secret})
    assert response.headers["x-request-id"]
    records = [json.loads(item.message) for item in caplog.records if item.name == "relapaw.request"]
    assert records
    record = records[-1]
    assert record["event"] == "http_request"
    assert record["path"] == "/api/v1/auth/otp/request"
    assert secret not in caplog.text


def test_request_log_uses_route_template_and_never_logs_resource_ids(client, caplog):
    with caplog.at_level(logging.INFO, logger="relapaw.request"):
        client.get("/api/v1/pets/987654321")
        client.get("/not-a-route/private-value-123")
    records = [json.loads(item.message) for item in caplog.records if item.name == "relapaw.request"]
    assert records[-2]["path"] == "/api/v1/pets/{pet_id}"
    assert records[-1]["path"] == "<unmatched>"
    assert "987654321" not in caplog.text
    assert "private-value-123" not in caplog.text


@pytest.mark.parametrize("pepper", ["", "   ", "short-secret"])
def test_production_rejects_missing_or_weak_session_pepper(pepper):
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(_env_file=None, **production_values(RELAPAW_SESSION_PEPPER=pepper))


def test_invalid_external_request_id_is_replaced(client):
    response = client.get("/health", headers={"X-Request-ID": "invalid request id with spaces"})
    assert response.headers["x-request-id"] != "invalid request id with spaces"
    accepted = client.get("/health", headers={"X-Request-ID": "trace-123"})
    assert accepted.headers["x-request-id"] == "trace-123"


class FakeConnection:
    def __init__(self, revision):
        self.revision = revision

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, _statement):
        return None

    def scalar(self, _statement):
        return self.revision


class FakeEngine:
    def __init__(self, revision=SCHEMA_REVISION, error=None):
        self.revision = revision
        self.error = error

    def connect(self):
        if self.error:
            raise self.error
        return FakeConnection(self.revision)


def test_readiness_checks_database_and_exact_schema(client, monkeypatch):
    monkeypatch.setattr("app.main.engine", FakeEngine())
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"

    monkeypatch.setattr("app.main.engine", FakeEngine("old-revision"))
    mismatch = client.get("/ready")
    assert mismatch.status_code == 503
    assert mismatch.json() == {"status": "not_ready", "database": "ok", "schema": "mismatch"}

    monkeypatch.setattr("app.main.engine", FakeEngine(error=RuntimeError("secret database detail")))
    unavailable = client.get("/ready")
    assert unavailable.status_code == 503
    assert unavailable.json() == {"status": "not_ready", "database": "unavailable", "schema": "unknown"}
    assert "secret database detail" not in unavailable.text
