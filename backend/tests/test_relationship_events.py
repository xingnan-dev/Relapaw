def create_episode(client, pet_id: int):
    return client.post("/api/v1/episodes/complete", json={
        "pet_id": pet_id,
        "happened_at": "2026-10-20T08:00:00Z",
        "episode_type": "relationship_observation",
        "raw_owner_input": "Both cats rested on opposite ends of the same sofa.",
        "observations": [{"behavior_type": "shared_rest", "description": "Both remained on the sofa for ten minutes.", "source_type": "owner_direct"}],
        "owner_interpretations": [{"interpretation": "I wondered whether they were becoming more comfortable nearby."}],
        "safety_check": {"result": "NORMAL", "danger_signals": [], "acknowledged_at": "2026-10-20T08:01:00Z"},
    }).json()


def test_owner_pet_and_pet_pet_relationship_events_keep_layers_and_history(client, pet):
    second = client.post("/api/v1/pets", json={"name": "Nori", "species": "cat"}).json()
    episode = create_episode(client, pet["id"])
    owner_event = client.post("/api/v1/relationship-events", json={
        "relationship_kind": "OWNER_PET", "participant_pet_ids": [pet["id"]],
        "happened_at": "2026-10-20T07:00:00Z", "observation_type": "OWNER_INTERACTION",
        "observation_text": "Mochi approached and remained beside the owner for five minutes.",
        "owner_interpretation": "I felt that the morning routine was familiar to her.",
    })
    assert owner_event.status_code == 201, owner_event.text
    assert owner_event.json()["observation_text"].startswith("Mochi approached")
    assert owner_event.json()["interpretations"][0]["interpretation"].startswith("I felt")

    created = client.post("/api/v1/relationship-events", json={
        "relationship_kind": "PET_PET", "participant_pet_ids": [pet["id"], second["id"]],
        "happened_at": "2026-10-20T08:00:00Z", "observation_type": "SHARED_REST",
        "observation_text": "Both cats rested on opposite ends of the same sofa for ten minutes.",
        "owner_interpretation": "I wondered whether they were more comfortable sharing the room.",
        "source_episode_id": episode["id"],
    })
    assert created.status_code == 201, created.text
    event = created.json()
    assert {item["pet_id"] for item in event["participants"]} == {pet["id"], second["id"]}
    assert event["source_episode_id"] == episode["id"]
    assert event["revisions"][0]["observation_text"] == event["observation_text"]

    updated = client.put(f"/api/v1/relationship-events/{event['id']}", json={
        "relationship_kind": "PET_PET", "participant_pet_ids": [pet["id"], second["id"]],
        "happened_at": "2026-10-20T08:05:00Z", "observation_type": "INTERACTION",
        "observation_text": "Nori sniffed the sofa edge; both cats then remained two metres apart.",
        "owner_interpretation": "I am not sure what the distance meant.",
        "source_episode_id": episode["id"],
    })
    assert updated.status_code == 200, updated.text
    assert len(updated.json()["revisions"]) == 2
    assert len(updated.json()["interpretations"]) == 2
    assert updated.json()["current_owner_interpretation"] == "I am not sure what the distance meant."
    withdrawn = client.put(f"/api/v1/relationship-events/{event['id']}", json={
        "relationship_kind": "PET_PET", "participant_pet_ids": [pet["id"], second["id"]],
        "happened_at": "2026-10-20T08:05:00Z", "observation_type": "INTERACTION",
        "observation_text": "Nori sniffed the sofa edge; both cats then remained two metres apart.",
        "owner_interpretation": None, "source_episode_id": episode["id"],
    })
    assert withdrawn.status_code == 200
    assert withdrawn.json()["current_owner_interpretation"] is None
    assert len(withdrawn.json()["interpretations"]) == 2
    assert withdrawn.json()["revisions"][-1]["owner_interpretation"] is None
    assert client.get(f"/api/v1/pets/{second['id']}/relationship-events").json()[0]["id"] == event["id"]


def test_relationship_participants_and_source_are_validated(client, pet):
    second = client.post("/api/v1/pets", json={"name": "Nori", "species": "cat"}).json()
    other_episode = create_episode(client, second["id"])
    invalid_shape = client.post("/api/v1/relationship-events", json={
        "relationship_kind": "PET_PET", "participant_pet_ids": [pet["id"]],
        "happened_at": "2026-10-20T08:00:00Z", "observation_type": "CONFLICT", "observation_text": "One hiss occurred.",
    })
    assert invalid_shape.status_code == 422
    invalid_layer = client.post("/api/v1/relationship-events", json={
        "relationship_kind": "PET_PET", "participant_pet_ids": [pet["id"], second["id"]],
        "happened_at": "2026-10-20T08:00:00Z", "observation_type": "OWNER_INTERACTION",
        "observation_text": "This type belongs to owner-pet records.",
    })
    assert invalid_layer.status_code == 422
    mismatch = client.post("/api/v1/relationship-events", json={
        "relationship_kind": "OWNER_PET", "participant_pet_ids": [pet["id"]],
        "happened_at": "2026-10-20T08:00:00Z", "observation_type": "OWNER_INTERACTION",
        "observation_text": "Mochi remained near the owner.", "source_episode_id": other_episode["id"],
    })
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "RELATIONSHIP_SOURCE_MISMATCH"

    valid = client.post("/api/v1/relationship-events", json={
        "relationship_kind": "PET_PET", "participant_pet_ids": [pet["id"], second["id"]],
        "happened_at": "2026-10-20T08:00:00Z", "observation_type": "AVOIDANCE",
        "observation_text": "Nori left the room when Mochi approached the doorway.",
    }).json()
    assert client.patch(f"/api/v1/pets/{second['id']}", json={"archived": True}).status_code == 200
    assert client.get(f"/api/v1/pets/{pet['id']}/relationship-events").json() == []
    blocked = client.put(f"/api/v1/relationship-events/{valid['id']}", json={
        "relationship_kind": "OWNER_PET", "participant_pet_ids": [pet["id"]],
        "happened_at": "2026-10-20T08:00:00Z", "observation_type": "OWNER_INTERACTION",
        "observation_text": "Must not repurpose an archived relationship event.",
    })
    assert blocked.status_code == 404
