import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.domain.enums import DangerSignal
from app.domain.medical_safety import MEDICAL_SAFETY_MANIFEST


def production_settings(**overrides):
    values = {
        "RELAPAW_ENV": "production",
        "RELAPAW_DEPLOYMENT_VERSION": "5af287e-test",
        "database_url": "postgresql+psycopg://relapaw:secret@db/relapaw",
        "cors_origins": ["https://beta.relapaw.example"],
        "RELAPAW_SESSION_PEPPER": "a-production-secret-that-is-not-the-default",
        "RELAPAW_TERMS_VERSION": "terms-v1",
        "RELAPAW_PRIVACY_VERSION": "privacy-v1",
        "RELAPAW_LEGAL_DOCUMENTS_APPROVED": True,
        "RELAPAW_MEDICAL_REVIEW_STATUS": "APPROVED",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_medical_manifest_and_api_enum_cannot_drift():
    assert MEDICAL_SAFETY_MANIFEST["version"] == "medical-safety/v1"
    assert MEDICAL_SAFETY_MANIFEST["status"] == "PENDING"
    assert set(MEDICAL_SAFETY_MANIFEST["signals"]) == {item.value for item in DangerSignal}
    assert all(value is None for value in MEDICAL_SAFETY_MANIFEST["review"].values())


def test_production_refuses_unreviewed_medical_content():
    with pytest.raises(ValidationError, match="Veterinarian-approved"):
        production_settings()


def test_production_refuses_enabled_unqualified_model(monkeypatch):
    approve_medical_manifest(monkeypatch)
    with pytest.raises(ValidationError, match="qualified model"):
        production_settings(RELAPAW_AI_ENABLED=True)


def approve_medical_manifest(monkeypatch):
    monkeypatch.setitem(MEDICAL_SAFETY_MANIFEST, "status", "APPROVED")
    monkeypatch.setitem(MEDICAL_SAFETY_MANIFEST, "review", {
        "reviewer_name": "Test Reviewer",
        "reviewer_credential": "TEST-ONLY",
        "reviewed_at": "2026-10-20T00:00:00Z",
        "approval_reference": "test-fixture",
    })


def test_qualified_model_requires_exact_repository_record(monkeypatch):
    approve_medical_manifest(monkeypatch)
    with pytest.raises(ValidationError, match="MODEL_QUALIFICATION_ID"):
        production_settings(RELAPAW_MODEL_QUALIFICATION="QUALIFIED")

    with pytest.raises(ValidationError, match="in-repository qualification"):
        production_settings(
            RELAPAW_AI_ENABLED=True,
            RELAPAW_MODEL_QUALIFICATION="QUALIFIED",
            RELAPAW_MODEL_QUALIFICATION_ID="qualification-2026-10-reviewed",
            RELAPAW_OPENAI_MODEL="reviewed-model",
        )

    from app.domain.model_qualification import MODEL_QUALIFICATIONS
    monkeypatch.setitem(MODEL_QUALIFICATIONS, "qualification-2026-10-reviewed", {
        "status": "APPROVED",
        "provider": "openai",
        "model": "reviewed-model",
        "base_url": "https://api.openai.com/v1",
        "prompt_contract": "text-understanding/v5-grounded-claims",
        "input_contract": "understanding-input/v1",
        "output_contract": "understanding-output/v1",
    })
    configured = production_settings(
        RELAPAW_AI_ENABLED=True,
        RELAPAW_MODEL_QUALIFICATION="QUALIFIED",
        RELAPAW_MODEL_QUALIFICATION_ID="qualification-2026-10-reviewed",
        RELAPAW_OPENAI_MODEL="reviewed-model",
    )
    assert configured.ai_enabled is True
    assert configured.model_qualification_id == "qualification-2026-10-reviewed"

    with pytest.raises(ValidationError, match="in-repository qualification"):
        production_settings(
            RELAPAW_AI_ENABLED=True,
            RELAPAW_MODEL_QUALIFICATION="QUALIFIED",
            RELAPAW_MODEL_QUALIFICATION_ID="qualification-2026-10-reviewed",
            RELAPAW_OPENAI_MODEL="different-model",
        )
