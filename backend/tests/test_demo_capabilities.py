from app.api.routes.capabilities import get_ai_enabled
from app.main import app
from app.schemas.analysis import AdapterDescriptor
from app.services.understanding_adapter import get_text_understanding_adapter


class CountingAdapter:
    descriptor = AdapterDescriptor(
        adapter_name="counting-fake",
        model_provider="test",
        model_name="never-called",
        model_version="1",
        prompt_contract_version="text-understanding/v1",
    )

    def __init__(self, *, fail_on_call: bool = True):
        self.calls = 0
        self.fail_on_call = fail_on_call

    def analyze(self, payload):
        self.calls += 1
        if self.fail_on_call:
            raise AssertionError("adapter must not be called")
        return {
            "contract_version": "understanding-output/v1",
            "claims": [{
                "claim_type": "behavior_hypothesis",
                "statement": "One possible explanation depends on the immediate context.",
                "confidence_label": "LOW",
                "evidence": [{"evidence_key": payload.evidence[0].key, "role": "SUPPORTS"}],
                "uncertainties": [{
                    "kind": "LIMITED_OBSERVATION",
                    "description": "This is based on a single synthetic observation.",
                }],
            }],
        }


def episode_payload(pet_id: int, safety_result: str = "NORMAL") -> dict:
    return {
        "pet_id": pet_id,
        "happened_at": "2026-10-17T09:30:00+08:00",
        "episode_type": "behavior_change",
        "raw_owner_input": "Synthetic demo observation",
        "observations": [{
            "behavior_type": "pause",
            "description": "Paused at the doorway for 20 seconds",
            "source_type": "owner_direct",
        }],
        "owner_interpretations": [],
        "safety_check": {
            "result": safety_result,
            "danger_signals": ["breathing_difficulty"] if safety_result == "ESCALATE_TO_VET" else [],
            "acknowledged_at": "2026-10-17T09:31:00+08:00",
        },
    }


def test_capabilities_default_to_ai_disabled(client):
    response = client.get("/api/v1/capabilities")

    assert response.status_code == 200
    assert response.json() == {
        "environment": "development",
        "synthetic_data": False,
        "dataset_version": None,
        "ai_analysis_enabled": False,
        "model_qualification": "NOT_QUALIFIED",
        "model_qualification_id": None,
        "medical_knowledge_version": "medical-safety/v1",
        "medical_review_status": "PENDING",
    }


def test_raw_ai_switch_cannot_bypass_model_qualification(client, pet, monkeypatch):
    episode = client.post("/api/v1/episodes/complete", json=episode_payload(pet["id"])).json()
    adapter = CountingAdapter()
    app.dependency_overrides[get_text_understanding_adapter] = lambda: adapter
    monkeypatch.setattr("app.api.routes.capabilities.settings.ai_enabled", True)
    monkeypatch.setattr("app.api.routes.capabilities.settings.model_qualification", "NOT_QUALIFIED")

    capabilities = client.get("/api/v1/capabilities").json()
    assert capabilities["ai_analysis_enabled"] is False
    assert capabilities["model_qualification"] == "NOT_QUALIFIED"
    response = client.post(
        f"/api/v1/episodes/{episode['id']}/analysis-runs",
        json={"request_id": "unqualified-model"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "MODEL_NOT_QUALIFIED"
    assert adapter.calls == 0


def test_normal_episode_cannot_create_analysis_when_feature_is_disabled(client, pet):
    episode = client.post("/api/v1/episodes/complete", json=episode_payload(pet["id"])).json()
    adapter = CountingAdapter()
    app.dependency_overrides[get_text_understanding_adapter] = lambda: adapter

    response = client.post(
        f"/api/v1/episodes/{episode['id']}/analysis-runs",
        json={"request_id": "disabled-demo"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FEATURE_DISABLED"
    assert adapter.calls == 0
    assert client.get(f"/api/v1/episodes/{episode['id']}/analysis-runs").json() == []


def test_missing_safety_still_reports_required_before_feature_flag(client, pet):
    episode = client.post("/api/v1/episodes", json={
        "pet_id": pet["id"],
        "happened_at": "2026-10-17T09:30:00+08:00",
        "episode_type": "legacy_note",
        "raw_owner_input": "Synthetic legacy note without a safety check",
    }).json()
    adapter = CountingAdapter()
    app.dependency_overrides[get_text_understanding_adapter] = lambda: adapter

    response = client.post(
        f"/api/v1/episodes/{episode['id']}/analysis-runs",
        json={"request_id": "missing-safety-first"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SAFETY_CHECK_REQUIRED"
    assert adapter.calls == 0


def test_safety_blocking_precedes_feature_flag_and_never_calls_adapter(client, pet):
    episode = client.post(
        "/api/v1/episodes/complete",
        json=episode_payload(pet["id"], "ESCALATE_TO_VET"),
    ).json()
    adapter = CountingAdapter()
    app.dependency_overrides[get_text_understanding_adapter] = lambda: adapter

    response = client.post(
        f"/api/v1/episodes/{episode['id']}/analysis-runs",
        json={"request_id": "safety-first"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "BLOCKED_BY_SAFETY"
    assert adapter.calls == 0


def test_explicit_enable_keeps_existing_analysis_path_available(client, pet):
    episode = client.post("/api/v1/episodes/complete", json=episode_payload(pet["id"])).json()
    app.dependency_overrides[get_ai_enabled] = lambda: True
    adapter = CountingAdapter(fail_on_call=False)
    app.dependency_overrides[get_text_understanding_adapter] = lambda: adapter

    response = client.post(
        f"/api/v1/episodes/{episode['id']}/analysis-runs",
        json={"request_id": "enabled-demo"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "COMPLETED"
    assert adapter.calls == 1
