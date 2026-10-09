from datetime import datetime, timedelta, timezone

import pytest

import app.services.follow_ups as follow_up_service


def episode_payload(pet_id: int, raw="Original record"):
    return {
        "pet_id": pet_id,
        "happened_at": datetime.now(timezone.utc).isoformat(),
        "episode_type": "behavior_change",
        "raw_owner_input": raw,
        "observations": [{"behavior_type": "hiding", "description": "Stayed under the table", "source_type": "owner_direct"}],
        "owner_interpretations": [{"interpretation": "I thought the visitor affected her"}],
        "safety_check": {"result": "NORMAL", "danger_signals": [], "acknowledged_at": datetime.now(timezone.utc).isoformat()},
    }


def complete_payload(outcome="IMPROVED"):
    return {
        "outcome": outcome,
        "happened_at": datetime.now(timezone.utc).isoformat(),
        "episode_type": "follow_up",
        "raw_owner_input": "Follow-up raw input",
        "context": {"follow_up_label": outcome},
        "observations": [{"behavior_type": "movement", "description": "Walked out from under the table", "source_type": "owner_direct"}],
        "owner_interpretations": [{"interpretation": "I think she was more comfortable"}],
        "safety_check": {"result": "NORMAL", "danger_signals": [], "acknowledged_at": datetime.now(timezone.utc).isoformat()},
    }


def create_episode(client, pet_id: int, raw="Original record"):
    response = client.post("/api/v1/episodes/complete", json=episode_payload(pet_id, raw))
    assert response.status_code == 201
    return response.json()


def schedule(client, episode_id: int, hours=2):
    scheduled_at = datetime.now(timezone.utc) + timedelta(hours=hours)
    response = client.post(f"/api/v1/episodes/{episode_id}/follow-ups", json={"scheduled_at": scheduled_at.isoformat()})
    assert response.status_code == 201
    return response.json()


def test_schedule_requires_timezone_and_existing_episode(client, pet):
    episode = create_episode(client, pet["id"])
    created = schedule(client, episode["id"])
    assert created["status"] == "PENDING"
    assert created["scheduled_at"].endswith("Z")
    naive = client.post(f"/api/v1/episodes/{episode['id']}/follow-ups", json={"scheduled_at": "2027-01-01T10:00:00"})
    assert naive.status_code == 422
    assert naive.json()["error"]["code"] == "VALIDATION_ERROR"
    missing = client.post("/api/v1/episodes/999/follow-ups", json={"scheduled_at": "2027-01-01T10:00:00Z"})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "EPISODE_NOT_FOUND"


def test_pet_list_status_timing_and_isolation(client, pet, monkeypatch):
    episode = create_episode(client, pet["id"])
    follow_up = schedule(client, episode["id"], 2)
    other = client.post("/api/v1/pets", json={"name": "Other", "species": "dog"}).json()
    schedule(client, create_episode(client, other["id"], "Other pet")["id"], 2)

    class FutureDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = datetime.fromisoformat(follow_up["scheduled_at"].replace("Z", "+00:00")) + timedelta(hours=1)
            return value.astimezone(tz) if tz else value

    monkeypatch.setattr(follow_up_service, "datetime", FutureDateTime)
    response = client.get(f"/api/v1/pets/{pet['id']}/follow-ups?status=PENDING&timing=ACTIONABLE")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["source_raw_owner_input"] == "Original record"
    assert response.json()[0]["timing_status"] in {"DUE", "OVERDUE"}
    assert all(item["source_raw_owner_input"] != "Other pet" for item in response.json())


def test_complete_creates_new_episode_and_bidirectional_links(client, pet):
    source = create_episode(client, pet["id"])
    follow_up = schedule(client, source["id"])
    response = client.post(f"/api/v1/follow-ups/{follow_up['id']}/complete", json=complete_payload())
    assert response.status_code == 200
    result = response.json()
    assert result["id"] != source["id"]
    assert result["pet_id"] == source["pet_id"]
    assert result["observations"][0]["description"].startswith("Walked")
    assert result["owner_interpretations"][0]["interpretation"].startswith("I think")
    assert result["safety_check"]["id"] != source["safety_check"]["id"]
    assert "FOLLOW_UP" in {item["source_type"] for item in result["evidence_references"]}
    assert result["result_of_follow_up"]["source_episode_id"] == source["id"]

    source_after = client.get(f"/api/v1/episodes/{source['id']}").json()
    assert source_after["raw_owner_input"] == "Original record"
    assert source_after["scheduled_follow_ups"][0]["result_episode_id"] == result["id"]
    assert source_after["scheduled_follow_ups"][0]["outcome"] == "IMPROVED"


def test_complete_can_create_manual_veterinary_escalation(client, pet):
    follow_up = schedule(client, create_episode(client, pet["id"])["id"])
    body = complete_payload("WORSENED")
    body["safety_check"] = {"result": "ESCALATE_TO_VET", "danger_signals": ["breathing_difficulty"], "acknowledged_at": datetime.now(timezone.utc).isoformat()}
    result = client.post(f"/api/v1/follow-ups/{follow_up['id']}/complete", json=body).json()
    assert result["veterinary_escalations"][0]["status"] == "OPEN"


def test_completion_failure_rolls_back_new_episode_and_follow_up(client, pet, monkeypatch):
    source = create_episode(client, pet["id"])
    follow_up = schedule(client, source["id"])
    original = follow_up_service.EvidenceReference
    monkeypatch.setattr(follow_up_service, "EvidenceReference", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("forced failure")))
    with pytest.raises(RuntimeError, match="forced failure"):
        client.post(f"/api/v1/follow-ups/{follow_up['id']}/complete", json=complete_payload())
    monkeypatch.setattr(follow_up_service, "EvidenceReference", original)
    pending = client.get(f"/api/v1/pets/{pet['id']}/follow-ups?status=PENDING").json()
    assert pending[0]["id"] == follow_up["id"]
    assert pending[0]["result_episode_id"] is None
    assert client.get(f"/api/v1/pets/{pet['id']}/timeline").json()["total"] == 1


def test_repeat_completion_and_cancelled_completion_are_rejected(client, pet):
    first = schedule(client, create_episode(client, pet["id"])["id"])
    assert client.post(f"/api/v1/follow-ups/{first['id']}/complete", json=complete_payload()).status_code == 200
    repeated = client.post(f"/api/v1/follow-ups/{first['id']}/complete", json=complete_payload())
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "FOLLOW_UP_ALREADY_COMPLETED"

    second = schedule(client, create_episode(client, pet["id"], "Second")["id"])
    cancelled = client.post(f"/api/v1/follow-ups/{second['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    rejected = client.post(f"/api/v1/follow-ups/{second['id']}/complete", json=complete_payload())
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "FOLLOW_UP_CANCELLED"


def test_cancel_and_missing_follow_up_errors(client, pet):
    follow_up = schedule(client, create_episode(client, pet["id"])["id"])
    assert client.post(f"/api/v1/follow-ups/{follow_up['id']}/cancel").status_code == 200
    repeated = client.post(f"/api/v1/follow-ups/{follow_up['id']}/cancel")
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "FOLLOW_UP_CANCELLED"
    missing = client.post("/api/v1/follow-ups/999/cancel")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "FOLLOW_UP_NOT_FOUND"


def test_source_and_result_episode_deletion_is_blocked(client, pet):
    source = create_episode(client, pet["id"])
    follow_up = schedule(client, source["id"])
    source_delete = client.delete(f"/api/v1/episodes/{source['id']}")
    assert source_delete.status_code == 409
    assert source_delete.json()["error"]["code"] == "EPISODE_HAS_FOLLOW_UPS"
    result = client.post(f"/api/v1/follow-ups/{follow_up['id']}/complete", json=complete_payload()).json()
    result_delete = client.delete(f"/api/v1/episodes/{result['id']}")
    assert result_delete.status_code == 409
    assert result_delete.json()["error"]["code"] == "EPISODE_HAS_FOLLOW_UPS"
