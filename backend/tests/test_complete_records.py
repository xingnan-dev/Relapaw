def complete_payload(pet_id: int) -> dict:
    return {
        "pet_id": pet_id,
        "happened_at": "2026-10-08T09:30:00+08:00",
        "episode_type": "behavior_change",
        "raw_owner_input": "She stayed behind the sofa and skipped breakfast.",
        "duration_seconds": 1200,
        "frequency_count": 1,
        "intensity": 2,
        "location": "living room",
        "trigger_context": "A visitor arrived shortly before.",
        "observations": [
            {
                "behavior_type": "hiding",
                "description": "Stayed behind the sofa for 20 minutes",
                "source_type": "owner_direct",
                "measured_value": 20,
                "unit": "minutes",
            }
        ],
        "owner_interpretations": [
            {"interpretation": "I think the visitor made her nervous"}
        ],
        "safety_check": {
            "result": "NORMAL",
            "danger_signals": [],
            "acknowledged_at": "2026-10-08T09:35:00+08:00",
        },
    }


def test_complete_episode_is_created_as_one_aggregate(client, pet):
    response = client.post("/api/v1/episodes/complete", json=complete_payload(pet["id"]))

    assert response.status_code == 201
    body = response.json()
    assert body["pet_id"] == pet["id"]
    assert body["duration_seconds"] == 1200
    assert body["observations"][0]["description"] == "Stayed behind the sofa for 20 minutes"
    assert body["owner_interpretations"][0]["interpretation"].startswith("I think")
    assert body["safety_check"]["result"] == "NORMAL"
    assert [item["source_type"] for item in body["evidence_references"]] == [
        "RAW_OWNER_INPUT",
        "OBSERVATION",
        "OWNER_INTERPRETATION",
    ]
    assert body["evidence_references"][1]["source_id"] == body["observations"][0]["id"]

    reread = client.get(f"/api/v1/pets/{pet['id']}/timeline").json()["items"][0]
    assert reread["safety_check"]["acknowledged_at"].endswith("Z")
    assert reread["evidence_references"][0]["observed_at"].endswith("Z")


def test_manual_danger_signal_creates_open_escalation(client, pet):
    payload = complete_payload(pet["id"])
    payload["safety_check"] = {
        "result": "ESCALATE_TO_VET",
        "danger_signals": ["breathing_difficulty"],
        "acknowledged_at": "2026-10-08T09:35:00Z",
    }
    response = client.post("/api/v1/episodes/complete", json=payload)

    assert response.status_code == 201
    episode_id = response.json()["id"]
    escalations = client.get(f"/api/v1/episodes/{episode_id}/veterinary-escalations")
    assert escalations.status_code == 200
    assert escalations.json()[0]["status"] == "OPEN"
    assert "breathing_difficulty" in escalations.json()[0]["reason"]


def test_complete_episode_can_link_a_plan_for_the_same_pet(client, pet):
    plan = client.post(
        f"/api/v1/pets/{pet['id']}/observation-plans",
        json={"goal": "Observe hiding"},
    ).json()
    payload = complete_payload(pet["id"])
    payload["plan_id"] = plan["id"]

    response = client.post("/api/v1/episodes/complete", json=payload)

    assert response.status_code == 201
    assert response.json()["plan_links"][0]["plan_id"] == plan["id"]


def test_invalid_plan_does_not_leave_a_partial_episode(client, pet):
    payload = complete_payload(pet["id"])
    payload["plan_id"] = 999

    response = client.post("/api/v1/episodes/complete", json=payload)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "OBSERVATION_PLAN_NOT_FOUND"
    timeline = client.get(f"/api/v1/pets/{pet['id']}/timeline").json()
    assert timeline["total"] == 0


def test_complete_episode_rejects_inconsistent_safety_input_without_writing(client, pet):
    payload = complete_payload(pet["id"])
    payload["safety_check"]["danger_signals"] = ["severe_bleeding"]

    response = client.post("/api/v1/episodes/complete", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert client.get(f"/api/v1/pets/{pet['id']}/timeline").json()["total"] == 0


def test_complete_episode_requires_at_least_one_observation(client, pet):
    payload = complete_payload(pet["id"])
    payload["observations"] = []

    response = client.post("/api/v1/episodes/complete", json=payload)

    assert response.status_code == 422
    assert client.get(f"/api/v1/pets/{pet['id']}/timeline").json()["total"] == 0
