def create_plan(client, pet_id, status="ACTIVE"):
    return client.post(f"/api/v1/pets/{pet_id}/observation-plans", json={
        "status": status,
        "start_at": "2026-10-08T08:00:00+08:00",
        "end_at": "2026-10-15T08:00:00+08:00",
        "goal": "Observe doorway pauses",
        "items": [
            {"label": "Pause duration", "description": "Record seconds", "is_required": True},
            {"label": "Direction faced", "is_required": False},
        ],
    })


def test_plan_items_detail_and_order(client, pet):
    created = create_plan(client, pet["id"])
    assert created.status_code == 201
    body = created.json()
    assert [item["label"] for item in body["items"]] == ["Pause duration", "Direction faced"]
    assert [item["sort_order"] for item in body["items"]] == [0, 1]
    detail = client.get(f"/api/v1/observation-plans/{body['id']}")
    assert detail.status_code == 200
    assert detail.json()["pet_id"] == pet["id"]


def test_plan_state_transitions_and_terminal_guard(client, pet):
    draft = create_plan(client, pet["id"], "DRAFT").json()
    invalid = client.patch(f"/api/v1/observation-plans/{draft['id']}", json={"status": "COMPLETED"})
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "INVALID_OBSERVATION_PLAN_TRANSITION"
    assert client.patch(f"/api/v1/observation-plans/{draft['id']}", json={"status": "ACTIVE"}).status_code == 200
    assert client.patch(f"/api/v1/observation-plans/{draft['id']}", json={"status": "COMPLETED"}).status_code == 200
    terminal = client.patch(f"/api/v1/observation-plans/{draft['id']}", json={"goal": "Changed"})
    assert terminal.status_code == 409
    assert terminal.json()["error"]["code"] == "OBSERVATION_PLAN_TERMINAL"


def test_plan_pet_isolation_and_episode_link(client, pet):
    other = client.post("/api/v1/pets", json={"name": "Other", "species": "cat"}).json()
    plan = create_plan(client, pet["id"]).json()
    assert client.get(f"/api/v1/pets/{other['id']}/observation-plans").json() == []
    payload = {
        "pet_id": other["id"], "happened_at": "2026-10-08T09:00:00Z", "episode_type": "daily_observation",
        "raw_owner_input": "note", "observations": [{"behavior_type": "daily", "description": "stood still", "source_type": "owner_direct"}],
        "owner_interpretations": [], "safety_check": {"result": "NORMAL", "danger_signals": [], "acknowledged_at": "2026-10-08T09:00:00Z"}, "plan_id": plan["id"],
    }
    response = client.post("/api/v1/episodes/complete", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PLAN_PET_MISMATCH"


def test_plan_dates_require_timezone(client, pet):
    response = client.post(f"/api/v1/pets/{pet['id']}/observation-plans", json={"goal": "Observe", "start_at": "2026-10-08T08:00:00", "items": [{"label": "item"}]})
    assert response.status_code == 422
