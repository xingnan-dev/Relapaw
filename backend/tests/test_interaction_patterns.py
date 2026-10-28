def event(client, pet_ids, happened_at, observation_type, text):
    kind = "OWNER_PET" if len(pet_ids) == 1 else "PET_PET"
    response = client.post("/api/v1/relationship-events", json={
        "relationship_kind": kind,
        "participant_pet_ids": pet_ids,
        "happened_at": happened_at,
        "observation_type": observation_type,
        "observation_text": text,
    })
    assert response.status_code == 201, response.text
    return response.json()


def candidate_payload(pet_id, supports, contradictions):
    return {
        "relationship_kind": "OWNER_PET",
        "participant_pet_ids": [pet_id],
        "initial_self_report": "我最初觉得它更喜欢傍晚靠近。",
        "title": "傍晚主动靠近的候选模式",
        "observable_pattern": "在多次傍晚记录中，它会主动走近并停留。",
        "support_event_ids": supports,
        "contradiction_event_ids": contradictions,
        "counterevidence_summary": "有一次它在相同时间保持距离。",
        "confidence_limit": "记录数量仍少，只描述已观察到的时段，不代表固定性格。",
    }


def test_pattern_requires_multiple_events_and_time_coverage(client, pet):
    first = event(client, [pet["id"]], "2026-10-01T08:00:00Z", "OWNER_INTERACTION", "主动靠近并停留两分钟。")
    second = event(client, [pet["id"]], "2026-10-03T08:00:00Z", "OWNER_INTERACTION", "主动靠近并坐在一米内。")
    third = event(client, [pet["id"]], "2026-10-04T08:00:00Z", "OTHER", "在门边停留，没有靠近。")
    response = client.post("/api/v1/interaction-patterns", json=candidate_payload(pet["id"], [first["id"], second["id"]], [third["id"]]))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INTERACTION_PATTERN_COVERAGE_TOO_SHORT"


def test_pattern_preserves_support_contradiction_versions_and_separate_memory_consent(client, pet):
    first = event(client, [pet["id"]], "2026-10-01T08:00:00Z", "OWNER_INTERACTION", "主动靠近并停留两分钟。")
    second = event(client, [pet["id"]], "2026-10-08T08:00:00Z", "OWNER_INTERACTION", "主动靠近并坐在一米内。")
    third = event(client, [pet["id"]], "2026-10-15T08:00:00Z", "OTHER", "在门边停留，没有靠近。")
    response = client.post("/api/v1/interaction-patterns", json=candidate_payload(pet["id"], [first["id"], second["id"]], [third["id"]]))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["evidence_count"] == 3
    assert body["coverage_start"] == "2026-10-01T08:00:00Z"
    assert body["coverage_end"] == "2026-10-15T08:00:00Z"
    assert [item["role"] for item in body["evidences"]] == ["SUPPORTS", "SUPPORTS", "CONTRADICTS"]
    assert body["evidences"][0]["observation_snapshot"] == "主动靠近并停留两分钟。"
    assert body["generator_version"] == "interaction-pattern/owner-reviewed-v1"
    assert body["status"] == "ELIGIBLE"
    assert body["memory_status"] == "NOT_INCLUDED"
    assert body["revisions"][0]["revision_number"] == 1

    blocked = client.post(f"/api/v1/interaction-patterns/{body['id']}/decisions", json={"action": "INCLUDE_IN_MEMORY"})
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "INTERACTION_PATTERN_CONFIRMATION_REQUIRED"
    confirmed = client.post(f"/api/v1/interaction-patterns/{body['id']}/decisions", json={"action": "CONFIRM"}).json()
    assert confirmed["status"] == "CONFIRMED"
    assert confirmed["memory_status"] == "NOT_INCLUDED"
    assert confirmed["decisions"][0]["action"] == "CONFIRM"
    assert confirmed["decisions"][0]["previous_status"] == "ELIGIBLE"
    included = client.post(f"/api/v1/interaction-patterns/{body['id']}/decisions", json={"action": "INCLUDE_IN_MEMORY"}).json()
    assert included["memory_status"] == "INCLUDED"
    assert [item["action"] for item in included["decisions"]] == ["CONFIRM", "INCLUDE_IN_MEMORY"]

    update = client.put(f"/api/v1/interaction-patterns/{body['id']}", json={
        "title": body["title"],
        "observable_pattern": "在两次傍晚记录中主动走近；另一次没有靠近。",
        "counterevidence_summary": body["counterevidence_summary"],
        "confidence_limit": body["confidence_limit"],
        "change_summary": "把反例写入正文",
    })
    assert update.status_code == 200
    assert [item["revision_number"] for item in update.json()["revisions"]] == [1, 2]
    assert update.json()["revisions"][1]["change_summary"] == "把反例写入正文"
    assert update.json()["evidences"][0]["observation_snapshot"] == "主动靠近并停留两分钟。"

    withdrawn = client.post(f"/api/v1/interaction-patterns/{body['id']}/decisions", json={"action": "WITHDRAW"}).json()
    assert withdrawn["status"] == "WITHDRAWN"
    assert withdrawn["memory_status"] == "WITHDRAWN"
    assert [item["action"] for item in withdrawn["decisions"]] == ["CONFIRM", "INCLUDE_IN_MEMORY", "WITHDRAW"]
    listed = client.get(f"/api/v1/pets/{pet['id']}/interaction-patterns").json()
    assert [item["id"] for item in listed] == [body["id"]]

    deleted = client.delete(f"/api/v1/interaction-patterns/{body['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/pets/{pet['id']}/interaction-patterns").json() == []
