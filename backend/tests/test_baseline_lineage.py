import pytest

import app.services.baseline as baseline_service


def complete_episode(client, pet_id: int, day: int, value: int):
    response = client.post("/api/v1/episodes/complete", json={
        "pet_id": pet_id,
        "happened_at": f"2026-10-{day:02d}T00:00:00Z",
        "episode_type": "pause",
        "raw_owner_input": f"Owner wording {day}",
        "duration_seconds": value,
        "frequency_count": value,
        "intensity": min(value, 5),
        "observations": [{
            "behavior_type": "pause",
            "description": f"Observed {value}",
            "source_type": "owner_direct",
            "measured_value": value,
            "unit": "seconds",
        }],
        "owner_interpretations": [{"interpretation": f"Owner thought {day}"}],
        "safety_check": {
            "result": "NORMAL",
            "danger_signals": [],
            "acknowledged_at": f"2026-10-{day:02d}T00:05:00Z",
        },
    })
    assert response.status_code == 201
    return response.json()


def recompute(client, pet_id: int, window="7d"):
    return client.post(
        f"/api/v1/pets/{pet_id}/baseline-snapshots/recompute",
        json={"window": window, "as_of": "2026-10-12T00:00:00Z"},
    )


def test_lineage_is_field_level_and_covers_current_and_comparison_windows(client, pet):
    current = complete_episode(client, pet["id"], 8, 3)
    comparison = complete_episode(client, pet["id"], 2, 2)

    response = recompute(client, pet["id"])

    assert response.status_code == 201
    body = response.json()
    current_items = [item for item in body["evidences"] if item["window_segment"] == "CURRENT"]
    comparison_items = [item for item in body["evidences"] if item["window_segment"] == "COMPARISON"]
    assert len(current_items) == len(comparison_items) == 5
    duration = next(item for item in current_items if item["field_path"] == "duration_seconds")
    measured = next(item for item in current_items if item["field_path"] == "measured_value")
    frequency = next(item for item in current_items if item["field_path"] == "episode_type")
    assert duration["episode_id"] == current["id"]
    assert duration["observation_id"] is None
    assert duration["value_snapshot"] == 3.0
    assert duration["metric_key"] == "duration_seconds||seconds"
    assert measured["observation_id"] == current["observations"][0]["id"]
    assert measured["source_snapshot"] == {
        "episode_type": "pause",
        "behavior_type": "pause",
        "unit": "seconds",
    }
    assert frequency["metric_key"] == "episode_type_frequency|pause"
    assert frequency["value_snapshot"] == "pause"
    assert {item["episode_id"] for item in comparison_items} == {comparison["id"]}


def test_edit_preserves_old_value_snapshot_and_recompute_creates_new_lineage(client, pet):
    episode = complete_episode(client, pet["id"], 8, 3)
    first = recompute(client, pet["id"]).json()
    old_measured = next(item for item in first["evidences"] if item["field_path"] == "measured_value")
    update = {
        "happened_at": episode["happened_at"],
        "episode_type": episode["episode_type"],
        "raw_owner_input": "Edited wording",
        "duration_seconds": 9,
        "frequency_count": episode["frequency_count"],
        "intensity": episode["intensity"],
        "observations": [{
            "behavior_type": "pause",
            "description": "Edited observation",
            "source_type": "owner_direct",
            "measured_value": 9,
            "unit": "seconds",
        }],
        "owner_interpretations": [{"interpretation": "Edited owner interpretation"}],
    }
    assert client.put(f"/api/v1/episodes/{episode['id']}", json=update).status_code == 200

    old = client.get(f"/api/v1/baseline-snapshots/{first['id']}").json()
    preserved = next(item for item in old["evidences"] if item["id"] == old_measured["id"])
    assert old["is_stale"] is True
    assert preserved["episode_id"] == episode["id"]
    assert preserved["observation_id"] is None
    assert preserved["value_snapshot"] == 3.0
    refreshed = recompute(client, pet["id"]).json()
    new_measured = next(item for item in refreshed["evidences"] if item["field_path"] == "measured_value")
    assert refreshed["id"] != first["id"]
    assert refreshed["is_stale"] is False
    assert new_measured["value_snapshot"] == 9.0
    assert new_measured["observation_id"] is not None


def test_deleting_baseline_episode_removes_derived_snapshot_and_recomputes_empty(client, pet):
    episode = complete_episode(client, pet["id"], 8, 3)
    snapshot = recompute(client, pet["id"]).json()

    deletion = client.delete(f"/api/v1/episodes/{episode['id']}")

    assert deletion.status_code == 204
    assert client.get(f"/api/v1/baseline-snapshots/{snapshot['id']}").status_code == 404
    refreshed = recompute(client, pet["id"]).json()
    assert refreshed["status"] == "EMPTY"
    assert refreshed["sample_count"] == 0
    assert refreshed["evidences"] == []


def test_new_relevant_episode_makes_old_snapshot_stale_but_future_episode_does_not(client, pet):
    complete_episode(client, pet["id"], 8, 3)
    snapshot = recompute(client, pet["id"]).json()
    complete_episode(client, pet["id"], 9, 4)
    assert client.get(f"/api/v1/baseline-snapshots/{snapshot['id']}").json()["is_stale"] is True
    refreshed = recompute(client, pet["id"]).json()
    complete_episode(client, pet["id"], 13, 5)
    assert client.get(f"/api/v1/baseline-snapshots/{refreshed['id']}").json()["is_stale"] is False


def test_lineage_failure_rolls_back_snapshot_and_does_not_mutate_source_aggregates(client, pet, monkeypatch):
    episode = complete_episode(client, pet["id"], 8, 3)
    before = client.get(f"/api/v1/episodes/{episode['id']}").json()
    original = baseline_service.BaselineEvidence
    monkeypatch.setattr(
        baseline_service,
        "BaselineEvidence",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("forced lineage failure")),
    )
    with pytest.raises(RuntimeError, match="forced lineage failure"):
        recompute(client, pet["id"])
    monkeypatch.setattr(baseline_service, "BaselineEvidence", original)

    missing = client.get(
        f"/api/v1/pets/{pet['id']}/baseline-snapshots/latest", params={"window": "7d"}
    )
    after = client.get(f"/api/v1/episodes/{episode['id']}").json()
    assert missing.status_code == 404
    assert after["raw_owner_input"] == before["raw_owner_input"]
    assert after["observations"] == before["observations"]
    assert after["owner_interpretations"] == before["owner_interpretations"]
    assert after["safety_check"] == before["safety_check"]
