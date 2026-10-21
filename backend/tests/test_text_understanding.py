import pytest

import app.services.understanding as understanding_service
from app.main import app
from app.api.routes.capabilities import get_ai_enabled
from app.schemas.analysis import AdapterDescriptor
from app.services.understanding_adapter import AdapterError, DisabledAdapter, get_text_understanding_adapter


def complete_payload(pet_id: int, *, safety_result="NORMAL") -> dict:
    danger_signals = ["breathing_difficulty"] if safety_result == "ESCALATE_TO_VET" else []
    return {
        "pet_id": pet_id,
        "happened_at": "2026-10-09T09:30:00+08:00",
        "episode_type": "behavior_change",
        "raw_owner_input": "Mochi paused at the doorway and I wondered whether she was uncertain.",
        "observations": [{
            "behavior_type": "pause",
            "description": "Paused at the doorway for 25 seconds",
            "source_type": "owner_direct",
            "measured_value": 25,
            "unit": "seconds",
        }],
        "owner_interpretations": [{"interpretation": "I think she may have been uncertain"}],
        "safety_check": {
            "result": safety_result,
            "danger_signals": danger_signals,
            "acknowledged_at": "2026-10-09T09:35:00+08:00",
        },
    }


class FakeAdapter:
    descriptor = AdapterDescriptor(
        adapter_name="test-fake",
        model_provider="test",
        model_name="contract-fixture",
        model_version="1",
        prompt_contract_version="text-understanding/v1",
    )

    def __init__(self, mode="valid"):
        self.mode = mode
        self.calls = []

    def analyze(self, payload):
        self.calls.append(payload)
        if self.mode == "provider_timeout":
            raise AdapterError("MODEL_TIMEOUT", "Model provider request timed out", 504)
        if self.mode == "invalid_contract":
            return {"claims": [{"statement": "missing required fields"}], "diagnosis": "forbidden"}
        evidence_key = "evidence:999999" if self.mode == "foreign_evidence" else payload.evidence[0].key
        return {
            "contract_version": "understanding-output/v1",
            "claims": [{
                "claim_type": "behavior_hypothesis",
                "statement": "One possible explanation is that the doorway pause related to the immediate context.",
                "confidence_label": "LOW",
                "evidence": [{"evidence_key": evidence_key, "role": "SUPPORTS"}],
                "uncertainties": [{
                    "kind": "LIMITED_OBSERVATION",
                    "description": "This is based on one short owner-recorded episode.",
                }],
            }],
        }


def create_episode(client, pet_id: int, *, safety_result="NORMAL") -> dict:
    response = client.post("/api/v1/episodes/complete", json=complete_payload(pet_id, safety_result=safety_result))
    assert response.status_code == 201
    return response.json()


def use_adapter(adapter):
    app.dependency_overrides[get_text_understanding_adapter] = lambda: adapter
    app.dependency_overrides[get_ai_enabled] = lambda: True


def test_analysis_preserves_input_lenses_and_persists_traceability(client, pet):
    episode = create_episode(client, pet["id"])
    adapter = FakeAdapter()
    use_adapter(adapter)

    response = client.post(f"/api/v1/episodes/{episode['id']}/analysis-runs", json={"request_id": "run-1"})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["adapter_name"] == "test-fake"
    assert body["prompt_contract_version"] == "text-understanding/v1"
    assert body["is_stale"] is False
    assert body["input_snapshot"]["raw_owner_input"] == episode["raw_owner_input"]
    assert body["input_snapshot"]["observations"][0]["description"] == episode["observations"][0]["description"]
    assert body["input_snapshot"]["owner_interpretations"][0]["interpretation"] == episode["owner_interpretations"][0]["interpretation"]
    claim = body["claims"][0]
    assert claim["status"] == "PROPOSED"
    assert claim["confidence_label"] == "LOW"
    assert claim["evidence_references"][0]["excerpt"] == episode["raw_owner_input"]
    assert claim["uncertainties"][0]["kind"] == "LIMITED_OBSERVATION"
    assert client.get(f"/api/v1/episodes/{episode['id']}").json()["raw_owner_input"] == episode["raw_owner_input"]


def test_analysis_persists_provider_resolved_model_version_after_reservation(client, pet):
    episode = create_episode(client, pet["id"])

    class ResolvingAdapter(FakeAdapter):
        def __init__(self):
            super().__init__()
            self.version = "requested-model"

        @property
        def descriptor(self):
            return AdapterDescriptor(
                adapter_name="test-fake", model_provider="test", model_name="contract-fixture",
                model_version=self.version, prompt_contract_version="text-understanding/v1",
            )

        def analyze(self, payload):
            self.version = "resolved-model-2026-10-20"
            return super().analyze(payload)

    use_adapter(ResolvingAdapter())
    response = client.post(
        f"/api/v1/episodes/{episode['id']}/analysis-runs",
        json={"request_id": "resolved-version"},
    )
    assert response.status_code == 201
    assert response.json()["model_version"] == "resolved-model-2026-10-20"


def test_analysis_is_idempotent_for_episode_request_id(client, pet):
    episode = create_episode(client, pet["id"])
    adapter = FakeAdapter()
    use_adapter(adapter)
    url = f"/api/v1/episodes/{episode['id']}/analysis-runs"

    first = client.post(url, json={"request_id": "same-request"})
    second = client.post(url, json={"request_id": "same-request"})

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert len(adapter.calls) == 1
    assert len(client.get(url).json()) == 1


@pytest.mark.parametrize("safety_result", ["NEED_MORE_INFO", "ESCALATE_TO_VET"])
def test_safety_must_exist_and_every_non_normal_result_blocks_adapter(client, pet, safety_result):
    bare = client.post("/api/v1/episodes", json={
        "pet_id": pet["id"],
        "happened_at": "2026-10-09T09:30:00Z",
        "episode_type": "note",
        "raw_owner_input": "A bare legacy note",
    }).json()
    adapter = FakeAdapter()
    use_adapter(adapter)
    missing = client.post(f"/api/v1/episodes/{bare['id']}/analysis-runs", json={"request_id": "missing-safety"})
    assert missing.status_code == 409
    assert missing.json()["error"]["code"] == "SAFETY_CHECK_REQUIRED"

    unsafe = create_episode(client, pet["id"], safety_result=safety_result)
    blocked = client.post(f"/api/v1/episodes/{unsafe['id']}/analysis-runs", json={"request_id": "blocked"})
    assert blocked.status_code == 201
    assert blocked.json()["status"] == "BLOCKED_BY_SAFETY"
    assert blocked.json()["claims"] == []
    assert adapter.calls == []


@pytest.mark.parametrize(
    ("mode", "expected_code"),
    [("invalid_contract", "MODEL_OUTPUT_INVALID"), ("foreign_evidence", "MODEL_EVIDENCE_INVALID")],
)
def test_invalid_model_results_are_rejected_but_audited(client, pet, mode, expected_code):
    episode = create_episode(client, pet["id"])
    use_adapter(FakeAdapter(mode))
    url = f"/api/v1/episodes/{episode['id']}/analysis-runs"

    response = client.post(url, json={"request_id": mode})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == expected_code
    runs = client.get(url).json()
    assert len(runs) == 1
    assert runs[0]["status"] == "FAILED"
    assert runs[0]["error_code"] == expected_code
    assert runs[0]["claims"] == []


def test_disabled_adapter_returns_real_not_configured_state(client, pet):
    episode = create_episode(client, pet["id"])
    use_adapter(DisabledAdapter())

    response = client.post(f"/api/v1/episodes/{episode['id']}/analysis-runs", json={"request_id": "disabled"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MODEL_NOT_CONFIGURED"
    runs = client.get(f"/api/v1/episodes/{episode['id']}/analysis-runs").json()
    assert runs[0]["adapter_name"] == "disabled"
    assert runs[0]["status"] == "FAILED"


def test_provider_failure_is_safely_audited_without_partial_claims(client, pet):
    episode = create_episode(client, pet["id"])
    adapter = FakeAdapter("provider_timeout")
    use_adapter(adapter)
    url = f"/api/v1/episodes/{episode['id']}/analysis-runs"

    response = client.post(url, json={"request_id": "provider-timeout"})

    assert response.status_code == 504
    assert response.json()["error"] == {
        "code": "MODEL_TIMEOUT",
        "message": "Model provider request timed out",
        "details": None,
    }
    runs = client.get(url).json()
    assert runs[0]["status"] == "FAILED"
    assert runs[0]["error_code"] == "MODEL_TIMEOUT"
    assert runs[0]["claims"] == []
    assert runs[0]["normalized_output"] is None


def test_claim_requires_one_final_user_decision(client, pet):
    episode = create_episode(client, pet["id"])
    use_adapter(FakeAdapter())
    run = client.post(f"/api/v1/episodes/{episode['id']}/analysis-runs", json={"request_id": "confirm"}).json()
    claim_id = run["claims"][0]["id"]

    confirmed = client.post(f"/api/v1/claims/{claim_id}/confirmations", json={"decision": "CONFIRMED", "note": "Matches later observation"})
    repeated = client.post(f"/api/v1/claims/{claim_id}/confirmations", json={"decision": "REJECTED"})

    assert confirmed.status_code == 201
    assert confirmed.json()["decision"] == "CONFIRMED"
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "CLAIM_ALREADY_DECIDED"
    reread = client.get(f"/api/v1/analysis-runs/{run['id']}").json()
    assert reread["claims"][0]["status"] == "CONFIRMED"
    assert reread["claims"][0]["confirmations"][0]["note"] == "Matches later observation"
    assert client.get(f"/api/v1/episodes/{episode['id']}").json()["observations"] == episode["observations"]


def test_analysis_snapshot_becomes_stale_then_is_removed_with_episode_content(client, pet):
    episode = create_episode(client, pet["id"])
    use_adapter(FakeAdapter())
    run = client.post(f"/api/v1/episodes/{episode['id']}/analysis-runs", json={"request_id": "stale"}).json()
    original_excerpt = run["claims"][0]["evidence_references"][0]["excerpt"]
    update = {
        "happened_at": episode["happened_at"],
        "episode_type": episode["episode_type"],
        "raw_owner_input": "Updated owner wording",
        "observations": [{"behavior_type": "pause", "description": "Paused for 30 seconds", "source_type": "owner_direct"}],
        "owner_interpretations": [{"interpretation": "I now think more context is needed"}],
    }
    assert client.put(f"/api/v1/episodes/{episode['id']}", json=update).status_code == 200

    reread = client.get(f"/api/v1/analysis-runs/{run['id']}").json()
    assert reread["is_stale"] is True
    assert reread["claims"][0]["evidence_references"][0]["excerpt"] == original_excerpt
    assert reread["claims"][0]["evidence_references"][0]["evidence_reference_id"] is None
    deletion = client.delete(f"/api/v1/episodes/{episode['id']}")
    assert deletion.status_code == 204
    assert client.get(f"/api/v1/episodes/{episode['id']}").status_code == 404
    assert client.get(f"/api/v1/analysis-runs/{run['id']}").status_code == 404


@pytest.mark.parametrize(
    ("suffix", "payload"),
    [
        ("observations", {"behavior_type": "look_back", "description": "Looked back once", "source_type": "owner_direct"}),
        ("owner-interpretations", {"interpretation": "I later noticed more context"}),
    ],
)
def test_incremental_source_changes_create_evidence_and_stale_existing_analysis(client, pet, suffix, payload):
    episode = create_episode(client, pet["id"])
    use_adapter(FakeAdapter())
    run = client.post(
        f"/api/v1/episodes/{episode['id']}/analysis-runs",
        json={"request_id": f"incremental-{suffix}"},
    ).json()

    added = client.post(f"/api/v1/episodes/{episode['id']}/{suffix}", json=payload)
    assert added.status_code == 201
    detail = client.get(f"/api/v1/episodes/{episode['id']}").json()
    source_type = "OBSERVATION" if suffix == "observations" else "OWNER_INTERPRETATION"
    assert any(
        item["source_type"] == source_type and item["source_id"] == added.json()["id"]
        for item in detail["evidence_references"]
    )
    assert client.get(f"/api/v1/analysis-runs/{run['id']}").json()["is_stale"] is True


def test_episode_can_change_while_provider_waits_without_breaking_snapshot(client, pet):
    episode = create_episode(client, pet["id"])

    class EditingAdapter(FakeAdapter):
        def analyze(self, payload):
            update = {
                "happened_at": episode["happened_at"],
                "episode_type": episode["episode_type"],
                "raw_owner_input": "Changed while provider was running",
                "observations": [{"behavior_type": "pause", "description": "Paused for 30 seconds", "source_type": "owner_direct"}],
                "owner_interpretations": [{"interpretation": "More context is needed"}],
            }
            assert client.put(f"/api/v1/episodes/{episode['id']}", json=update).status_code == 200
            return super().analyze(payload)

    use_adapter(EditingAdapter())

    response = client.post(
        f"/api/v1/episodes/{episode['id']}/analysis-runs",
        json={"request_id": "edit-during-provider"},
    )

    assert response.status_code == 201
    run = response.json()
    assert run["is_stale"] is True
    assert run["input_snapshot"]["raw_owner_input"] == episode["raw_owner_input"]
    assert run["claims"][0]["evidence_references"][0]["excerpt"] == episode["raw_owner_input"]
    assert run["claims"][0]["evidence_references"][0]["evidence_reference_id"] is None


def test_same_request_seen_while_provider_runs_returns_reservation_without_second_call(client, pet):
    episode = create_episode(client, pet["id"])
    url = f"/api/v1/episodes/{episode['id']}/analysis-runs"

    class ReentrantAdapter(FakeAdapter):
        def analyze(self, payload):
            nested = client.post(url, json={"request_id": "reserved-request"})
            assert nested.status_code == 201
            assert nested.json()["status"] == "RUNNING"
            return super().analyze(payload)

    adapter = ReentrantAdapter()
    use_adapter(adapter)
    response = client.post(url, json={"request_id": "reserved-request"})
    assert response.status_code == 201
    assert response.json()["status"] == "COMPLETED"
    assert len(adapter.calls) == 1
    assert len(client.get(url).json()) == 1


def test_episode_deleted_while_provider_runs_cannot_restore_analysis_content(client, pet):
    episode = create_episode(client, pet["id"])
    url = f"/api/v1/episodes/{episode['id']}/analysis-runs"

    class DeletingAdapter(FakeAdapter):
        def analyze(self, payload):
            assert client.delete(f"/api/v1/episodes/{episode['id']}").status_code == 204
            return super().analyze(payload)

    adapter = DeletingAdapter()
    use_adapter(adapter)
    response = client.post(url, json={"request_id": "delete-during-provider"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ANALYSIS_SOURCE_DELETED"
    assert len(adapter.calls) == 1
    assert client.get(f"/api/v1/episodes/{episode['id']}").status_code == 404


def test_analysis_write_failure_rolls_back_whole_aggregate(client, pet, monkeypatch):
    episode = create_episode(client, pet["id"])
    use_adapter(FakeAdapter())
    original = understanding_service.ClaimEvidenceReference
    monkeypatch.setattr(
        understanding_service,
        "ClaimEvidenceReference",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("forced analysis failure")),
    )
    with pytest.raises(RuntimeError, match="forced analysis failure"):
        client.post(f"/api/v1/episodes/{episode['id']}/analysis-runs", json={"request_id": "rollback"})
    monkeypatch.setattr(understanding_service, "ClaimEvidenceReference", original)
    assert client.get(f"/api/v1/episodes/{episode['id']}/analysis-runs").json() == []


def test_analysis_resources_have_uniform_not_found_errors(client):
    missing_run = client.get("/api/v1/analysis-runs/999")
    missing_claim = client.post("/api/v1/claims/999/confirmations", json={"decision": "REJECTED"})
    assert missing_run.status_code == missing_claim.status_code == 404
    assert missing_run.json()["error"]["code"] == "ANALYSIS_RUN_NOT_FOUND"
    assert missing_claim.json()["error"]["code"] == "CLAIM_NOT_FOUND"
