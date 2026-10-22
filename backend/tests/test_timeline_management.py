import pytest

import app.services.records as records_service


def payload(pet_id: int, happened_at="2026-10-08T09:30:00+08:00", episode_type="behavior_change"):
    return {
        "pet_id": pet_id,
        "happened_at": happened_at,
        "episode_type": episode_type,
        "raw_owner_input": "She stayed behind the sofa.",
        "context": {"weather": "rain"},
        "duration_seconds": 1200,
        "frequency_count": 1,
        "intensity": 2,
        "location": "living room",
        "trigger_context": "A visitor arrived.",
        "observations": [{"behavior_type": "hiding", "description": "Stayed behind the sofa for 20 minutes", "source_type": "owner_direct"}],
        "owner_interpretations": [{"interpretation": "I think the visitor affected her"}],
        "safety_check": {"result": "NORMAL", "danger_signals": [], "acknowledged_at": "2026-10-08T09:35:00+08:00"},
    }


def update_payload(body: dict):
    return {
        "happened_at": "2026-10-09T10:00:00+08:00",
        "episode_type": "followup_observation",
        "raw_owner_input": "She came out after breakfast.",
        "context": {"weather": "clear"},
        "duration_seconds": 300,
        "frequency_count": 2,
        "intensity": 1,
        "location": "kitchen",
        "trigger_context": "After breakfast",
        "observations": [{"behavior_type": "movement", "description": "Walked into the kitchen", "source_type": "owner_direct"}],
        "owner_interpretations": [{"interpretation": "I think she was more comfortable"}],
    }


def create(client, pet_id: int, **overrides):
    body = payload(pet_id, overrides.pop("happened_at", "2026-10-08T09:30:00+08:00"), overrides.pop("episode_type", "behavior_change"))
    body.update(overrides)
    response = client.post("/api/v1/episodes/complete", json=body)
    assert response.status_code == 201
    return response.json()


def test_complete_episode_detail_and_not_found(client, pet):
    episode = create(client, pet["id"])
    detail = client.get(f"/api/v1/episodes/{episode['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["observations"][0]["description"].startswith("Stayed")
    assert body["owner_interpretations"][0]["interpretation"].startswith("I think")
    assert body["safety_check"]["result"] == "NORMAL"
    assert len(body["evidence_references"]) == 3
    assert body["veterinary_escalations"] == []
    missing = client.get("/api/v1/episodes/999")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "EPISODE_NOT_FOUND"


def test_timeline_filters_count_page_and_stable_order(client, pet):
    plan = client.post(f"/api/v1/pets/{pet['id']}/observation-plans", json={"goal": "Observe"}).json()
    create(client, pet["id"], happened_at="2026-10-01T08:00:00Z", episode_type="feeding")
    create(client, pet["id"], happened_at="2026-10-08T08:00:00Z", episode_type="behavior_change", plan_id=plan["id"], raw_owner_input="first")
    create(client, pet["id"], happened_at="2026-10-08T08:00:00Z", episode_type="behavior_change", plan_id=plan["id"], raw_owner_input="second")
    url = f"/api/v1/pets/{pet['id']}/timeline?from=2026-10-08T00:00:00%2B08:00&to=2026-10-09T00:00:00%2B08:00&episode_type=behavior_change&plan_id={plan['id']}&page=1&page_size=1"
    result = client.get(url)
    assert result.status_code == 200
    assert result.json()["total"] == 2
    assert result.json()["has_more"] is True
    assert result.json()["items"][0]["raw_owner_input"] == "second"
    assert client.get(url.replace("page=1", "page=2")).json()["items"][0]["raw_owner_input"] == "first"


def test_timeline_rejects_naive_and_reversed_ranges(client, pet):
    naive = client.get(f"/api/v1/pets/{pet['id']}/timeline?from=2026-10-08T00:00:00")
    assert naive.status_code == 422
    assert naive.json()["error"]["code"] == "TIMEZONE_REQUIRED"
    reversed_range = client.get(f"/api/v1/pets/{pet['id']}/timeline?from=2026-10-09T00:00:00Z&to=2026-10-08T00:00:00Z")
    assert reversed_range.status_code == 422
    assert reversed_range.json()["error"]["code"] == "INVALID_TIMELINE_RANGE"


def test_timeline_searches_separate_lenses_and_filters_controlled_category(client, pet):
    matching = create(client, pet["id"],
        raw_owner_input="Quiet afternoon note",
        observations=[{"behavior_type": "owner-wording", "standardized_category": "RESTING", "description": "Curled on the blue blanket", "source_type": "owner_direct"}],
        owner_interpretations=[{"interpretation": "Perhaps the visitor made her cautious"}],
    )
    create(client, pet["id"], raw_owner_input="Ate dinner normally")

    by_fact = client.get(f"/api/v1/pets/{pet['id']}/timeline?q=blue%20blanket").json()
    assert [item["id"] for item in by_fact["items"]] == [matching["id"]]
    by_interpretation = client.get(f"/api/v1/pets/{pet['id']}/timeline?q=visitor%20made").json()
    assert [item["id"] for item in by_interpretation["items"]] == [matching["id"]]
    by_category = client.get(f"/api/v1/pets/{pet['id']}/timeline?category=RESTING").json()
    assert [item["id"] for item in by_category["items"]] == [matching["id"]]
    assert client.get(f"/api/v1/pets/{pet['id']}/timeline?category=NOT_REAL").status_code == 422


def test_timeline_never_leaks_another_pet(client, pet):
    other = client.post("/api/v1/pets", json={"name": "Other", "species": "dog"}).json()
    foreign_plan = client.post(f"/api/v1/pets/{other['id']}/observation-plans", json={"goal": "Other plan"}).json()
    create(client, other["id"], plan_id=foreign_plan["id"])
    own = client.get(f"/api/v1/pets/{pet['id']}/timeline?plan_id={foreign_plan['id']}")
    assert own.status_code == 200
    assert own.json()["items"] == []
    assert own.json()["total"] == 0


def test_update_replaces_lenses_and_evidence_but_preserves_safety(client, pet):
    episode = create(client, pet["id"])
    old_safety_id = episode["safety_check"]["id"]
    response = client.put(f"/api/v1/episodes/{episode['id']}", json=update_payload(episode))
    assert response.status_code == 200
    body = response.json()
    assert body["pet_id"] == pet["id"]
    assert body["raw_owner_input"] == "She came out after breakfast."
    assert [item["description"] for item in body["observations"]] == ["Walked into the kitchen"]
    assert [item["interpretation"] for item in body["owner_interpretations"]] == ["I think she was more comfortable"]
    assert body["safety_check"]["id"] == old_safety_id
    assert {item["source_id"] for item in body["evidence_references"]} == {body["id"], body["observations"][0]["id"], body["owner_interpretations"][0]["id"]}
    assert all(item["observed_at"] == body["happened_at"] for item in body["evidence_references"])


def test_update_forbids_pet_id_and_rolls_back_after_write_failure(client, pet, monkeypatch):
    episode = create(client, pet["id"])
    invalid = update_payload(episode)
    invalid["pet_id"] = 999
    assert client.put(f"/api/v1/episodes/{episode['id']}", json=invalid).status_code == 422

    original = records_service.EvidenceReference
    monkeypatch.setattr(records_service, "EvidenceReference", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("forced failure")))
    with pytest.raises(RuntimeError, match="forced failure"):
        client.put(f"/api/v1/episodes/{episode['id']}", json=update_payload(episode))
    monkeypatch.setattr(records_service, "EvidenceReference", original)
    reread = client.get(f"/api/v1/episodes/{episode['id']}").json()
    assert reread["raw_owner_input"] == episode["raw_owner_input"]
    assert reread["observations"][0]["description"] == episode["observations"][0]["description"]


def test_delete_cascades_aggregate_and_missing_is_404(client, pet):
    episode = create(client, pet["id"])
    response = client.delete(f"/api/v1/episodes/{episode['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/v1/episodes/{episode['id']}").status_code == 404
    assert client.get(f"/api/v1/pets/{pet['id']}/timeline").json()["total"] == 0
    missing = client.delete(f"/api/v1/episodes/{episode['id']}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "EPISODE_NOT_FOUND"
