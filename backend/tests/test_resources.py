def test_baseline_upsert(client, pet):
    response = client.put(
        f"/api/v1/pets/{pet['id']}/baseline",
        json={"feeding_pattern": {"summary": "Usually eats at 08:00"}},
    )
    assert response.status_code == 200
    assert response.json()["feeding_pattern"]["summary"] == "Usually eats at 08:00"


def test_life_event_create_and_enum_validation(client, pet):
    created = client.post(
        f"/api/v1/pets/{pet['id']}/life-events",
        json={"event_type": "moving", "happened_at": "2026-03-01T08:00:00+08:00"},
    )
    assert created.status_code == 201
    invalid = client.post(
        f"/api/v1/pets/{pet['id']}/life-events",
        json={"event_type": "invented", "happened_at": "2026-03-01T08:00:00Z"},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"


def test_observation_plan_create_update_and_invalid_pet(client, pet):
    created = client.post(
        f"/api/v1/pets/{pet['id']}/observation-plans",
        json={
            "status": "ACTIVE",
            "start_at": "2026-03-01T08:00:00Z",
            "end_at": "2026-03-03T08:00:00Z",
            "goal": "Record hiding duration",
            "items_to_observe": [{"label": "Minutes hidden"}],
        },
    )
    assert created.status_code == 201
    updated = client.patch(
        f"/api/v1/observation-plans/{created.json()['id']}", json={"status": "COMPLETED"}
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "COMPLETED"
    missing = client.post("/api/v1/pets/999/observation-plans", json={"goal": "Observe"})
    assert missing.status_code == 404


def test_veterinary_escalation_is_manual_structure(client, pet):
    episode = client.post(
        "/api/v1/episodes",
        json={
            "pet_id": pet["id"],
            "happened_at": "2026-03-01T08:00:00Z",
            "episode_type": "owner_concern",
            "raw_owner_input": "Manual note",
        },
    ).json()
    created = client.post(
        f"/api/v1/episodes/{episode['id']}/veterinary-escalations",
        json={"reason": "Owner chose to contact a vet", "status": "OPEN"},
    )
    assert created.status_code == 201
    assert created.json()["vet_brief"] is None

    missing_episode = client.post(
        "/api/v1/episodes/999/veterinary-escalations",
        json={"reason": "Manual check", "status": "OPEN"},
    )
    assert missing_episode.status_code == 404
    assert missing_episode.json()["error"]["code"] == "EPISODE_NOT_FOUND"

    invalid_status = client.patch(
        f"/api/v1/veterinary-escalations/{created.json()['id']}",
        json={"status": "AUTO_DIAGNOSED"},
    )
    assert invalid_status.status_code == 422
    assert invalid_status.json()["error"]["code"] == "VALIDATION_ERROR"


def test_veterinary_escalation_manual_lifecycle(client, pet):
    episode = client.post(
        "/api/v1/episodes",
        json={
            "pet_id": pet["id"],
            "happened_at": "2026-03-01T08:00:00Z",
            "episode_type": "owner_concern",
            "raw_owner_input": "Owner manually requested veterinary follow-up",
        },
    ).json()

    invalid_create = client.post(
        f"/api/v1/episodes/{episode['id']}/veterinary-escalations",
        json={"reason": "Manual check", "status": "CLOSED"},
    )
    assert invalid_create.status_code == 409
    assert invalid_create.json()["error"]["code"] == "INVALID_VETERINARY_ESCALATION_TRANSITION"

    created = client.post(
        f"/api/v1/episodes/{episode['id']}/veterinary-escalations",
        json={"reason": "Owner chose to contact a vet"},
    )
    assert created.status_code == 201
    escalation_id = created.json()["id"]

    shared = client.patch(
        f"/api/v1/veterinary-escalations/{escalation_id}",
        json={"status": "SHARED_WITH_VET", "vet_brief": "Shared by owner"},
    )
    assert shared.status_code == 200
    assert shared.json()["status"] == "SHARED_WITH_VET"
    assert shared.json()["vet_brief"] == "Shared by owner"

    backwards = client.patch(
        f"/api/v1/veterinary-escalations/{escalation_id}", json={"status": "OPEN"}
    )
    assert backwards.status_code == 409
    assert backwards.json()["error"]["code"] == "INVALID_VETERINARY_ESCALATION_TRANSITION"

    closed = client.patch(
        f"/api/v1/veterinary-escalations/{escalation_id}", json={"status": "CLOSED"}
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "CLOSED"

    terminal = client.patch(
        f"/api/v1/veterinary-escalations/{escalation_id}", json={"vet_brief": "Silently rewrite history"}
    )
    assert terminal.status_code == 409
    assert terminal.json()["error"]["code"] == "VETERINARY_ESCALATION_CLOSED"

    listed = client.get(f"/api/v1/episodes/{episode['id']}/veterinary-escalations")
    assert listed.status_code == 200
    assert listed.json()[0]["status"] == "CLOSED"
    assert listed.json()[0]["vet_brief"] == "Shared by owner"


def test_veterinary_escalation_update_missing_returns_unified_404(client):
    response = client.patch("/api/v1/veterinary-escalations/999", json={"status": "CLOSED"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VETERINARY_ESCALATION_NOT_FOUND"


def test_naive_datetime_is_rejected(client, pet):
    response = client.post(
        "/api/v1/episodes",
        json={
            "pet_id": pet["id"],
            "happened_at": "2026-03-01T08:00:00",
            "episode_type": "note",
            "raw_owner_input": "No timezone",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
