def create_episode(client, pet_id, happened_at="2026-01-01T08:00:00Z", text="Observed change"):
    return client.post(
        "/api/v1/episodes",
        json={
            "pet_id": pet_id,
            "happened_at": happened_at,
            "episode_type": "behavior_change",
            "raw_owner_input": text,
            "context": {"location": "home"},
        },
    )


def test_episode_creation(client, pet):
    response = create_episode(client, pet["id"])
    assert response.status_code == 201
    assert response.json()["pet_id"] == pet["id"]
    assert response.json()["observations"] == []


def test_observation_and_interpretation_are_separate(client, pet):
    episode_id = create_episode(client, pet["id"]).json()["id"]
    observed = client.post(
        f"/api/v1/episodes/{episode_id}/observations",
        json={
            "behavior_type": "hiding",
            "description": "Stayed under the bed for 20 minutes",
            "source_type": "owner_direct",
            "confidence": 0.9,
        },
    )
    interpreted = client.post(
        f"/api/v1/episodes/{episode_id}/owner-interpretations",
        json={"interpretation": "I think Mochi is upset with me"},
    )
    assert observed.status_code == 201
    assert interpreted.status_code == 201

    episode = client.get(f"/api/v1/pets/{pet['id']}/timeline").json()["items"][0]
    assert episode["observations"][0]["description"] == "Stayed under the bed for 20 minutes"
    assert episode["owner_interpretations"][0]["interpretation"] == "I think Mochi is upset with me"
    assert "interpretation" not in episode["observations"][0]
    assert "description" not in episode["owner_interpretations"][0]


def test_timeline_is_newest_first(client, pet):
    create_episode(client, pet["id"], "2026-01-01T08:00:00Z", "older")
    create_episode(client, pet["id"], "2026-02-01T08:00:00Z", "newer")
    timeline = client.get(f"/api/v1/pets/{pet['id']}/timeline")
    assert timeline.status_code == 200
    assert [item["raw_owner_input"] for item in timeline.json()["items"]] == ["newer", "older"]


def test_timeline_paginates_with_stable_same_time_order(client, pet):
    happened_at = "2026-03-01T08:00:00Z"
    create_episode(client, pet["id"], happened_at, "first")
    create_episode(client, pet["id"], happened_at, "second")
    response = client.get(f"/api/v1/pets/{pet['id']}/timeline?page=1&page_size=1")
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["has_more"] is True
    assert response.json()["items"][0]["raw_owner_input"] == "second"
