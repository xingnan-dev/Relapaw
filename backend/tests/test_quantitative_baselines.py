from datetime import datetime, timezone

import pytest

from app.services.baseline import (
    ALGORITHM_VERSION,
    EpisodeSource,
    ObservationValue,
    calculate_baseline,
    source_fingerprint,
    window_bounds,
)


def dt(day: int, hour: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, tzinfo=timezone.utc)


def source(
    source_id: int,
    happened_at: datetime,
    *,
    duration: int | None = None,
    frequency: int | None = None,
    intensity: int | None = None,
    episode_type: str = "behavior",
    observation_value: float | None = None,
    unit: str | None = "seconds",
    behavior_type: str = "pause",
) -> EpisodeSource:
    observations = () if observation_value is None else (
        ObservationValue(
            id=source_id,
            behavior_type=behavior_type,
            measured_value=observation_value,
            unit=unit,
            updated_at=happened_at,
        ),
    )
    return EpisodeSource(
        id=source_id,
        happened_at=happened_at,
        updated_at=happened_at,
        episode_type=episode_type,
        duration_seconds=duration,
        frequency_count=frequency,
        intensity=intensity,
        observations=observations,
    )


def test_standardized_category_and_unit_enable_comparison_without_replacing_raw_fields():
    sources = [
        EpisodeSource(
            id=index,
            happened_at=dt(10 + index),
            updated_at=dt(10 + index),
            episode_type="owner_wording",
            duration_seconds=None,
            frequency_count=None,
            intensity=None,
            observations=(ObservationValue(
                id=index,
                behavior_type=f"raw-owner-label-{index}",
                measured_value=float(index * 10),
                unit="owner-entered-seconds",
                updated_at=dt(10 + index),
                standardized_category="RESTING",
                standardized_unit="seconds",
            ),),
        )
        for index in (1, 2, 3)
    ]
    calculation = calculate_baseline("all", dt(20), sources)
    metric = next(item for item in calculation.metrics if item["field"] == "measured_value")
    assert metric["behavior_type"] == "RESTING"
    assert metric["unit"] == "seconds"
    assert metric["median"] == 20.0
    assert [item.observations[0].behavior_type for item in sources] == [
        "raw-owner-label-1", "raw-owner-label-2", "raw-owner-label-3"
    ]
    assert [item.observations[0].unit for item in sources] == ["owner-entered-seconds"] * 3


def metric(result, key):
    return next(item for item in result.metrics if item["key"] == key)


def test_window_boundaries_are_utc_inclusive_and_future_is_excluded():
    as_of = datetime(2026, 10, 12, 8, tzinfo=timezone.utc)
    start, end, comparison_start = window_bounds("7d", as_of)
    assert start == datetime(2026, 10, 5, 8, tzinfo=timezone.utc)
    assert end == as_of
    assert comparison_start == datetime(2026, 9, 28, 8, tzinfo=timezone.utc)
    sources = [
        source(1, start, duration=10),
        source(2, as_of, duration=20),
        source(3, as_of.replace(hour=9), duration=999),
    ]
    result = calculate_baseline("7d", as_of, sources)
    duration = metric(result, "duration_seconds||seconds")
    assert duration["count"] == 2
    assert duration["min"] == 10
    assert duration["max"] == 20
    assert result.sample_count == 2


@pytest.mark.parametrize(
    ("window", "expected_start"),
    [
        ("7d", datetime(2026, 10, 5, tzinfo=timezone.utc)),
        ("30d", datetime(2026, 9, 12, tzinfo=timezone.utc)),
        ("90d", datetime(2026, 7, 14, tzinfo=timezone.utc)),
        ("all", None),
    ],
)
def test_every_supported_window_has_a_frozen_boundary(window, expected_start):
    start, end, _comparison = window_bounds(window, dt(12))
    assert start == expected_start
    assert end == dt(12)


def test_metrics_are_grouped_by_field_behavior_and_unit_with_median():
    as_of = dt(12)
    sources = [
        source(1, dt(6), duration=10, frequency=1, intensity=2, observation_value=2, unit="seconds"),
        source(2, dt(7), duration=20, frequency=2, intensity=3, observation_value=4, unit="seconds"),
        source(3, dt(8), duration=30, frequency=3, intensity=4, observation_value=6, unit="seconds"),
        source(4, dt(9), observation_value=1, unit="minutes"),
    ]
    result = calculate_baseline("7d", as_of, sources)
    seconds = metric(result, "measured_value|pause|seconds")
    minutes = metric(result, "measured_value|pause|minutes")
    assert seconds == {
        "key": "measured_value|pause|seconds",
        "field": "measured_value",
        "behavior_type": "pause",
        "unit": "seconds",
        "count": 3,
        "min": 2.0,
        "max": 6.0,
        "median": 4.0,
        "status": "READY",
        "trend": None,
    }
    assert minutes["status"] == "INSUFFICIENT_DATA"
    assert minutes["count"] == 1
    assert metric(result, "duration_seconds||seconds")["median"] == 20.0
    assert metric(result, "frequency_count||count")["median"] == 2.0
    assert metric(result, "intensity||level")["median"] == 3.0
    frequency = metric(result, "episode_type_frequency|behavior")
    assert frequency["count"] == 4
    assert frequency["observation_days"] == 4
    assert result.status == "READY"


def test_trend_requires_three_samples_in_both_equal_non_overlapping_windows():
    as_of = dt(12)
    sources = [
        source(1, dt(6), duration=12),
        source(2, dt(7), duration=14),
        source(3, dt(8), duration=16),
        source(4, dt(1), duration=10),
        source(5, dt(2), duration=10),
        source(6, dt(3), duration=10),
    ]
    result = calculate_baseline("7d", as_of, sources)
    trend = metric(result, "duration_seconds||seconds")["trend"]
    assert trend == {
        "direction": "INCREASED",
        "current_median": 14.0,
        "comparison_median": 10.0,
        "threshold": 0.2,
        "comparison_count": 3,
    }
    all_history = calculate_baseline("all", as_of, sources)
    assert metric(all_history, "duration_seconds||seconds")["trend"] is None


def test_empty_and_insufficient_states_do_not_invent_trends():
    empty = calculate_baseline("30d", dt(12), [])
    assert empty.status == "EMPTY"
    assert empty.metrics == []
    one = calculate_baseline("30d", dt(12), [source(1, dt(10), duration=5)])
    assert one.status == "INSUFFICIENT_DATA"
    assert all(item["status"] == "INSUFFICIENT_DATA" for item in one.metrics)
    assert all(item["trend"] is None for item in one.metrics)


def test_fingerprint_is_stable_but_changes_with_structured_source_data():
    first = source(1, dt(10), duration=5, observation_value=2)
    same = source(1, dt(10), duration=5, observation_value=2)
    changed = source(1, dt(10), duration=6, observation_value=2)
    assert source_fingerprint(1, [first]) == source_fingerprint(1, [same])
    assert source_fingerprint(1, [first]) != source_fingerprint(1, [changed])
    assert source_fingerprint(1, [first]) != source_fingerprint(2, [first])


def complete_episode(client, pet_id: int, day: int, value: int):
    response = client.post("/api/v1/episodes/complete", json={
        "pet_id": pet_id,
        "happened_at": f"2026-10-{day:02d}T00:00:00Z",
        "episode_type": "pause",
        "raw_owner_input": f"Owner note {day}",
        "duration_seconds": value,
        "frequency_count": value,
        "intensity": min(value, 5),
        "observations": [{
            "behavior_type": "pause",
            "description": f"Observed value {value}",
            "source_type": "owner_direct",
            "measured_value": value,
            "unit": "seconds",
        }],
        "owner_interpretations": [{"interpretation": "Owner interpretation is not numeric evidence"}],
        "safety_check": {
            "result": "NORMAL",
            "danger_signals": [],
            "acknowledged_at": f"2026-10-{day:02d}T00:05:00Z",
        },
    })
    assert response.status_code == 201
    return response.json()


def test_recompute_is_idempotent_and_source_change_makes_old_snapshot_stale(client, pet):
    episodes = [complete_episode(client, pet["id"], day, index) for index, day in enumerate((6, 7, 8), 1)]
    manual = {"activity_pattern": {"source": "owner", "note": "manual baseline"}}
    assert client.put(f"/api/v1/pets/{pet['id']}/baseline", json=manual).status_code == 200
    url = f"/api/v1/pets/{pet['id']}/baseline-snapshots/recompute"
    payload = {"window": "7d", "as_of": "2026-10-12T00:00:00+00:00"}
    first = client.post(url, json=payload)
    repeated = client.post(url, json=payload)
    assert first.status_code == repeated.status_code == 201
    assert first.json()["id"] == repeated.json()["id"]
    assert first.json()["algorithm_version"] == ALGORITHM_VERSION
    assert first.json()["status"] == "READY"
    assert first.json()["sample_count"] == 3
    assert first.json()["is_stale"] is False

    changed = episodes[0]
    update = {
        "happened_at": changed["happened_at"],
        "episode_type": changed["episode_type"],
        "raw_owner_input": "Changed natural-language wording",
        "duration_seconds": 20,
        "frequency_count": changed["frequency_count"],
        "intensity": changed["intensity"],
        "observations": [{
            "behavior_type": "pause",
            "description": "Changed description",
            "source_type": "owner_direct",
            "measured_value": 20,
            "unit": "seconds",
        }],
        "owner_interpretations": [{"interpretation": "Still not treated as a numeric fact"}],
    }
    assert client.put(f"/api/v1/episodes/{changed['id']}", json=update).status_code == 200
    old = client.get(f"/api/v1/baseline-snapshots/{first.json()['id']}").json()
    assert old["is_stale"] is True
    refreshed = client.post(url, json=payload)
    assert refreshed.status_code == 201
    assert refreshed.json()["id"] != first.json()["id"]
    assert refreshed.json()["source_fingerprint"] != first.json()["source_fingerprint"]
    latest = client.get(
        f"/api/v1/pets/{pet['id']}/baseline-snapshots/latest", params={"window": "7d"}
    ).json()
    assert latest["id"] == refreshed.json()["id"]
    assert latest["is_stale"] is False
    assert client.get(f"/api/v1/pets/{pet['id']}/baseline").json()["activity_pattern"] == manual["activity_pattern"]


def test_as_of_requires_timezone_and_missing_snapshots_are_uniform(client, pet):
    invalid = client.post(
        f"/api/v1/pets/{pet['id']}/baseline-snapshots/recompute",
        json={"window": "7d", "as_of": "2026-10-12T00:00:00"},
    )
    missing = client.get(
        f"/api/v1/pets/{pet['id']}/baseline-snapshots/latest", params={"window": "7d"}
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "BASELINE_SNAPSHOT_NOT_FOUND"
