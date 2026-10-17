import pytest

import app.services.memory as memory_service
from app.api.routes.capabilities import get_ai_enabled
from app.main import app
from app.schemas.analysis import AdapterDescriptor
from app.services.understanding_adapter import get_text_understanding_adapter


class MemoryFakeAdapter:
    descriptor = AdapterDescriptor(
        adapter_name="memory-test-fake",
        model_provider="test",
        model_name="memory-fixture",
        model_version="1",
        prompt_contract_version="text-understanding/v1",
    )

    def analyze(self, payload):
        return {
            "contract_version": "understanding-output/v1",
            "claims": [{
                "claim_type": "possible_explanation",
                "statement": "The pause may relate to the immediate doorway context.",
                "confidence_label": "LOW",
                "evidence": [{"evidence_key": payload.evidence[0].key, "role": "SUPPORTS"}],
                "uncertainties": [{
                    "kind": "LIMITED_OBSERVATION",
                    "description": "This is based on one recorded episode.",
                }],
            }],
        }


def create_confirmed_claim(client, pet_id: int):
    episode = client.post("/api/v1/episodes/complete", json={
        "pet_id": pet_id,
        "happened_at": "2026-10-09T09:30:00+08:00",
        "episode_type": "behavior_change",
        "raw_owner_input": "Mochi paused at the doorway.",
        "observations": [{
            "behavior_type": "pause",
            "description": "Paused for 25 seconds",
            "source_type": "owner_direct",
            "measured_value": 25,
            "unit": "seconds",
        }],
        "owner_interpretations": [{"interpretation": "I wondered whether she was uncertain"}],
        "safety_check": {
            "result": "NORMAL",
            "danger_signals": [],
            "acknowledged_at": "2026-10-09T09:35:00+08:00",
        },
    }).json()
    app.dependency_overrides[get_text_understanding_adapter] = lambda: MemoryFakeAdapter()
    app.dependency_overrides[get_ai_enabled] = lambda: True
    run = client.post(
        f"/api/v1/episodes/{episode['id']}/analysis-runs", json={"request_id": "memory-run"}
    ).json()
    claim_id = run["claims"][0]["id"]
    confirmation = client.post(
        f"/api/v1/claims/{claim_id}/confirmations", json={"decision": "CONFIRMED"}
    )
    assert confirmation.status_code == 201
    return episode, run, claim_id


def test_only_confirmed_current_claim_can_become_candidate(client, pet):
    episode, run, claim_id = create_confirmed_claim(client, pet["id"])
    proposed_episode = client.post("/api/v1/episodes/complete", json={
        "pet_id": pet["id"],
        "happened_at": "2026-10-10T09:30:00Z",
        "episode_type": "note",
        "raw_owner_input": "Another note",
        "observations": [{
            "behavior_type": "pause",
            "description": "Paused briefly",
            "source_type": "owner_direct",
        }],
        "owner_interpretations": [{"interpretation": "I am not sure what it means"}],
        "safety_check": {"result": "NORMAL", "danger_signals": [], "acknowledged_at": "2026-10-10T09:31:00Z"},
    }).json()
    proposed_run = client.post(
        f"/api/v1/episodes/{proposed_episode['id']}/analysis-runs", json={"request_id": "proposed"}
    ).json()
    rejected = client.post(f"/api/v1/claims/{proposed_run['claims'][0]['id']}/memory-candidate")
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "CLAIM_NOT_CONFIRMED"

    created = client.post(f"/api/v1/claims/{claim_id}/memory-candidate")
    repeated = client.post(f"/api/v1/claims/{claim_id}/memory-candidate")
    assert created.status_code == repeated.status_code == 201
    assert created.json()["id"] == repeated.json()["id"]
    assert created.json()["state"] == "ELIGIBLE"
    assert created.json()["claim_snapshot"]["statement"] == run["claims"][0]["statement"]
    assert created.json()["evidence_snapshot"][0]["excerpt"] == episode["raw_owner_input"]


def test_include_withdraw_and_reinclude_are_append_only(client, pet):
    _, _, claim_id = create_confirmed_claim(client, pet["id"])
    candidate = client.post(f"/api/v1/claims/{claim_id}/memory-candidate").json()
    url = f"/api/v1/memory-candidates/{candidate['id']}/decisions"

    include = client.post(url, json={"request_id": "include-1", "decision": "INCLUDE", "note": "Keep this"})
    duplicate = client.post(url, json={"request_id": "include-1", "decision": "INCLUDE", "note": "Keep this"})
    conflict = client.post(url, json={"request_id": "include-1", "decision": "WITHDRAW", "note": "Keep this"})
    invalid_repeat = client.post(url, json={"request_id": "include-2", "decision": "INCLUDE"})
    withdrawn = client.post(url, json={"request_id": "withdraw-1", "decision": "WITHDRAW"})
    reincluded = client.post(url, json={"request_id": "include-3", "decision": "INCLUDE"})

    assert include.status_code == duplicate.status_code == 201
    assert len(duplicate.json()["decisions"]) == 1
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert invalid_repeat.status_code == 409
    assert invalid_repeat.json()["error"]["code"] == "INVALID_MEMORY_TRANSITION"
    assert withdrawn.json()["state"] == "WITHDRAWN"
    assert reincluded.json()["state"] == "ACTIVE"
    assert [item["decision"] for item in reincluded.json()["decisions"]] == ["INCLUDE", "WITHDRAW", "INCLUDE"]
    active = client.get(f"/api/v1/pets/{pet['id']}/long-term-memory").json()
    assert [item["id"] for item in active] == [candidate["id"]]


def test_stale_candidate_preserves_history_but_cannot_change(client, pet):
    episode, _, claim_id = create_confirmed_claim(client, pet["id"])
    candidate = client.post(f"/api/v1/claims/{claim_id}/memory-candidate").json()
    url = f"/api/v1/memory-candidates/{candidate['id']}/decisions"
    assert client.post(url, json={"request_id": "include", "decision": "INCLUDE"}).status_code == 201

    update = {
        "happened_at": episode["happened_at"],
        "episode_type": episode["episode_type"],
        "raw_owner_input": "Updated wording",
        "observations": [{"behavior_type": "pause", "description": "Paused for 30 seconds", "source_type": "owner_direct"}],
        "owner_interpretations": [{"interpretation": "More context is needed"}],
    }
    assert client.put(f"/api/v1/episodes/{episode['id']}", json=update).status_code == 200
    listed = client.get(f"/api/v1/pets/{pet['id']}/memory-candidates").json()
    assert listed[0]["state"] == "STALE"
    assert listed[0]["decisions"][0]["decision"] == "INCLUDE"
    assert client.get(f"/api/v1/pets/{pet['id']}/long-term-memory").json() == []
    withdrawn = client.post(url, json={"request_id": "withdraw", "decision": "WITHDRAW"})
    assert withdrawn.status_code == 201
    assert withdrawn.json()["state"] == "STALE"
    assert [item["decision"] for item in withdrawn.json()["decisions"]] == ["INCLUDE", "WITHDRAW"]
    rejected = client.post(url, json={"request_id": "reinclude", "decision": "INCLUDE"})
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "MEMORY_CANDIDATE_STALE"


def test_candidate_creation_rejects_claim_that_became_stale(client, pet):
    episode, _, claim_id = create_confirmed_claim(client, pet["id"])
    update = {
        "happened_at": episode["happened_at"],
        "episode_type": episode["episode_type"],
        "raw_owner_input": "Changed before candidate creation",
        "observations": [{"behavior_type": "pause", "description": "Changed observation", "source_type": "owner_direct"}],
        "owner_interpretations": [{"interpretation": "Changed interpretation"}],
    }
    assert client.put(f"/api/v1/episodes/{episode['id']}", json=update).status_code == 200
    response = client.post(f"/api/v1/claims/{claim_id}/memory-candidate")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CLAIM_STALE"


def test_decision_failure_rolls_back_without_partial_event(client, pet, monkeypatch):
    _, _, claim_id = create_confirmed_claim(client, pet["id"])
    candidate = client.post(f"/api/v1/claims/{claim_id}/memory-candidate").json()
    original = memory_service.MemoryDecision
    monkeypatch.setattr(
        memory_service,
        "MemoryDecision",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("forced decision failure")),
    )
    with pytest.raises(RuntimeError, match="forced decision failure"):
        client.post(
            f"/api/v1/memory-candidates/{candidate['id']}/decisions",
            json={"request_id": "failure", "decision": "INCLUDE"},
        )
    monkeypatch.setattr(memory_service, "MemoryDecision", original)
    reread = client.get(f"/api/v1/pets/{pet['id']}/memory-candidates").json()
    assert reread[0]["state"] == "ELIGIBLE"
    assert reread[0]["decisions"] == []
