def test_local_knowledge_and_episode_guidance_are_cited_and_fact_only(client, pet):
    knowledge = client.get("/api/v1/knowledge")
    assert knowledge.status_code == 200
    assert knowledge.json()["review_status"] == "UNREVIEWED_EXAMPLE"
    assert all(item["source"]["version"] for item in knowledge.json()["entries"])
    episode = client.post("/api/v1/episodes/complete", json={
        "pet_id": pet["id"], "happened_at": "2026-10-20T08:00:00Z", "episode_type": "observation",
        "raw_owner_input": "Stayed beside the door for 30 seconds", "duration_seconds": 30, "location": "door",
        "observations": [{"behavior_type": "resting", "description": "Stayed beside the door", "source_type": "owner_direct"}],
        "owner_interpretations": [{"interpretation": "May have been waiting"}],
        "safety_check": {"result": "NORMAL", "danger_signals": [], "acknowledged_at": "2026-10-20T08:01:00Z"},
    }).json()
    response = client.get(f"/api/v1/episodes/{episode['id']}/educational-guidance")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "EDUCATIONAL_ONLY"
    assert any("Stayed beside the door" in value for value in body["fact_summary"])
    assert all("May have been waiting" not in value for value in body["fact_summary"])
    assert all(item["source"]["locator"] for item in body["entries"])


def test_non_normal_safety_blocks_before_educational_content(client, pet):
    episode = client.post("/api/v1/episodes/complete", json={
        "pet_id": pet["id"], "happened_at": "2026-10-20T08:00:00Z", "episode_type": "observation", "raw_owner_input": "Collapsed",
        "observations": [{"behavior_type": "other", "description": "Could not stand", "source_type": "owner_direct"}], "owner_interpretations": [],
        "safety_check": {"result": "ESCALATE_TO_VET", "danger_signals": ["collapse_or_unable_to_stand"], "acknowledged_at": "2026-10-20T08:01:00Z"},
    }).json()
    response = client.get(f"/api/v1/episodes/{episode['id']}/educational-guidance")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EDUCATION_BLOCKED_BY_SAFETY"
