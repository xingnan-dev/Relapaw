from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from statistics import median
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import BaselineEvidence, BaselineSnapshot, Episode


ALGORITHM_VERSION = "quantitative-baseline/v1"
MINIMUM_SAMPLES = 3
TREND_THRESHOLD = 0.20
WINDOW_DAYS = {"7d": 7, "30d": 30, "90d": 90}


@dataclass(frozen=True)
class ObservationValue:
    id: int
    behavior_type: str
    measured_value: float | None
    unit: str | None
    updated_at: datetime


@dataclass(frozen=True)
class EpisodeSource:
    id: int
    happened_at: datetime
    updated_at: datetime
    episode_type: str
    duration_seconds: int | None
    frequency_count: int | None
    intensity: int | None
    observations: tuple[ObservationValue, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class BaselineCalculation:
    window_start: datetime | None
    window_end: datetime
    status: str
    sample_count: int
    metrics: list[dict[str, Any]]


@dataclass(frozen=True)
class LineageItem:
    episode_id: int
    observation_id: int | None
    source_type: str
    window_segment: str
    metric_key: str
    field_path: str
    value_snapshot: Any
    source_snapshot: dict[str, Any]
    observed_at: datetime
    source_updated_at: datetime


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def window_bounds(window: str, as_of: datetime) -> tuple[datetime | None, datetime, datetime | None]:
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must include a timezone offset")
    normalized = utc(as_of)
    if window == "all":
        return None, normalized, None
    if window not in WINDOW_DAYS:
        raise ValueError("Unsupported baseline window")
    duration = timedelta(days=WINDOW_DAYS[window])
    start = normalized - duration
    return start, normalized, start - duration


def source_fingerprint(pet_id: int, sources: list[EpisodeSource]) -> str:
    canonical = {
        "pet_id": pet_id,
        "sources": [
            {
                "id": source.id,
                "happened_at": utc(source.happened_at).isoformat(),
                "updated_at": utc(source.updated_at).isoformat(),
                "episode_type": source.episode_type,
                "duration_seconds": source.duration_seconds,
                "frequency_count": source.frequency_count,
                "intensity": source.intensity,
                "observations": [
                    {
                        "id": item.id,
                        "behavior_type": item.behavior_type,
                        "measured_value": item.measured_value,
                        "unit": item.unit,
                        "updated_at": utc(item.updated_at).isoformat(),
                    }
                    for item in sorted(source.observations, key=lambda value: value.id)
                ],
            }
            for source in sorted(sources, key=lambda value: value.id)
        ],
    }
    return hashlib.sha256(
        json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _finite_number(value: int | float | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _direction(current: float, comparison: float) -> str:
    if comparison == 0:
        return "STABLE" if current == 0 else "INCREASED"
    change = (current - comparison) / abs(comparison)
    if change >= TREND_THRESHOLD:
        return "INCREASED"
    if change <= -TREND_THRESHOLD:
        return "DECREASED"
    return "STABLE"


def _summary_metric(
    key: str,
    field_name: str,
    unit: str,
    values: list[float],
    comparison_values: list[float],
    behavior_type: str | None = None,
) -> dict[str, Any]:
    metric: dict[str, Any] = {
        "key": key,
        "field": field_name,
        "behavior_type": behavior_type,
        "unit": unit,
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "median": median(values),
        "status": "READY" if len(values) >= MINIMUM_SAMPLES else "INSUFFICIENT_DATA",
        "trend": None,
    }
    if len(values) >= MINIMUM_SAMPLES and len(comparison_values) >= MINIMUM_SAMPLES:
        current_median = float(median(values))
        comparison_median = float(median(comparison_values))
        metric["trend"] = {
            "direction": _direction(current_median, comparison_median),
            "current_median": current_median,
            "comparison_median": comparison_median,
            "threshold": TREND_THRESHOLD,
            "comparison_count": len(comparison_values),
        }
    return metric


def calculate_baseline(window: str, as_of: datetime, sources: list[EpisodeSource]) -> BaselineCalculation:
    window_start, window_end, comparison_start = window_bounds(window, as_of)
    current = [
        source for source in sources
        if utc(source.happened_at) <= window_end
        and (window_start is None or utc(source.happened_at) >= window_start)
    ]
    comparison = [] if comparison_start is None else [
        source for source in sources
        if comparison_start <= utc(source.happened_at) < window_start  # type: ignore[operator]
    ]

    grouped: dict[tuple[str, str | None, str], list[float]] = {}
    comparison_grouped: dict[tuple[str, str | None, str], list[float]] = {}

    def collect(target: dict[tuple[str, str | None, str], list[float]], entries: list[EpisodeSource]) -> None:
        for source in entries:
            for field_name, value, unit in (
                ("duration_seconds", source.duration_seconds, "seconds"),
                ("frequency_count", source.frequency_count, "count"),
                ("intensity", source.intensity, "level"),
            ):
                number = _finite_number(value)
                if number is not None:
                    target.setdefault((field_name, None, unit), []).append(number)
            for observation in source.observations:
                number = _finite_number(observation.measured_value)
                if number is not None and observation.unit:
                    target.setdefault(
                        ("measured_value", observation.behavior_type, observation.unit), []
                    ).append(number)

    collect(grouped, current)
    collect(comparison_grouped, comparison)
    metrics = [
        _summary_metric(
            key="|".join(part or "" for part in key),
            field_name=key[0],
            behavior_type=key[1],
            unit=key[2],
            values=values,
            comparison_values=comparison_grouped.get(key, []),
        )
        for key, values in sorted(grouped.items())
    ]

    current_types: dict[str, list[EpisodeSource]] = {}
    comparison_types: dict[str, list[EpisodeSource]] = {}
    for source in current:
        current_types.setdefault(source.episode_type, []).append(source)
    for source in comparison:
        comparison_types.setdefault(source.episode_type, []).append(source)
    for episode_type, entries in sorted(current_types.items()):
        previous = comparison_types.get(episode_type, [])
        count = len(entries)
        comparison_count = len(previous)
        trend = None
        if comparison_start is not None and count >= MINIMUM_SAMPLES and comparison_count >= MINIMUM_SAMPLES:
            trend = {
                "direction": _direction(float(count), float(comparison_count)),
                "current_count": count,
                "comparison_count": comparison_count,
                "threshold": TREND_THRESHOLD,
            }
        metrics.append({
            "key": f"episode_type_frequency|{episode_type}",
            "field": "episode_type_frequency",
            "episode_type": episode_type,
            "count": count,
            "observation_days": len({utc(item.happened_at).date().isoformat() for item in entries}),
            "status": "READY" if count >= MINIMUM_SAMPLES else "INSUFFICIENT_DATA",
            "trend": trend,
        })

    if not metrics:
        status = "EMPTY"
    elif any(metric["status"] == "READY" for metric in metrics):
        status = "READY"
    else:
        status = "INSUFFICIENT_DATA"
    return BaselineCalculation(
        window_start=window_start,
        window_end=window_end,
        status=status,
        sample_count=len(current),
        metrics=metrics,
    )


def build_lineage(window: str, as_of: datetime, sources: list[EpisodeSource]) -> list[LineageItem]:
    window_start, window_end, comparison_start = window_bounds(window, as_of)
    items: list[LineageItem] = []
    for source in sources:
        happened_at = utc(source.happened_at)
        if happened_at > window_end:
            continue
        if window_start is None:
            segment = "CURRENT"
        elif happened_at >= window_start:
            segment = "CURRENT"
        elif comparison_start is not None and happened_at >= comparison_start:
            segment = "COMPARISON"
        else:
            continue

        base_snapshot = {"episode_type": source.episode_type}
        items.append(LineageItem(
            episode_id=source.id,
            observation_id=None,
            source_type="EPISODE",
            window_segment=segment,
            metric_key=f"episode_type_frequency|{source.episode_type}",
            field_path="episode_type",
            value_snapshot=source.episode_type,
            source_snapshot=base_snapshot,
            observed_at=happened_at,
            source_updated_at=utc(source.updated_at),
        ))
        for field_name, value, unit in (
            ("duration_seconds", source.duration_seconds, "seconds"),
            ("frequency_count", source.frequency_count, "count"),
            ("intensity", source.intensity, "level"),
        ):
            number = _finite_number(value)
            if number is not None:
                items.append(LineageItem(
                    episode_id=source.id,
                    observation_id=None,
                    source_type="EPISODE",
                    window_segment=segment,
                    metric_key=f"{field_name}||{unit}",
                    field_path=field_name,
                    value_snapshot=number,
                    source_snapshot={**base_snapshot, "unit": unit},
                    observed_at=happened_at,
                    source_updated_at=utc(source.updated_at),
                ))
        for observation in source.observations:
            number = _finite_number(observation.measured_value)
            if number is not None and observation.unit:
                items.append(LineageItem(
                    episode_id=source.id,
                    observation_id=observation.id,
                    source_type="OBSERVATION",
                    window_segment=segment,
                    metric_key=f"measured_value|{observation.behavior_type}|{observation.unit}",
                    field_path="measured_value",
                    value_snapshot=number,
                    source_snapshot={
                        "episode_type": source.episode_type,
                        "behavior_type": observation.behavior_type,
                        "unit": observation.unit,
                    },
                    observed_at=happened_at,
                    source_updated_at=utc(observation.updated_at),
                ))
    return items


def _materialize_lineage(snapshot: BaselineSnapshot, items: list[LineageItem]) -> list[BaselineEvidence]:
    return [
        BaselineEvidence(
            snapshot_id=snapshot.id,
            episode_id=item.episode_id,
            observation_id=item.observation_id,
            source_type=item.source_type,
            window_segment=item.window_segment,
            metric_key=item.metric_key,
            field_path=item.field_path,
            value_snapshot=item.value_snapshot,
            source_snapshot=item.source_snapshot,
            observed_at=item.observed_at,
            source_updated_at=item.source_updated_at,
        )
        for item in items
    ]


def load_sources(db: Session, pet_id: int, window: str, as_of: datetime) -> list[EpisodeSource]:
    window_start, window_end, comparison_start = window_bounds(window, as_of)
    earliest = comparison_start if comparison_start is not None else window_start
    statement = (
        select(Episode)
        .where(Episode.pet_id == pet_id, Episode.happened_at <= window_end)
        .options(selectinload(Episode.observations))
        .order_by(Episode.id)
    )
    if earliest is not None:
        statement = statement.where(Episode.happened_at >= earliest)
    episodes = db.scalars(statement).all()
    return [
        EpisodeSource(
            id=episode.id,
            happened_at=episode.happened_at,
            updated_at=episode.updated_at,
            episode_type=episode.episode_type,
            duration_seconds=episode.duration_seconds,
            frequency_count=episode.frequency_count,
            intensity=episode.intensity,
            observations=tuple(
                ObservationValue(
                    id=item.id,
                    behavior_type=item.behavior_type,
                    measured_value=item.measured_value,
                    unit=item.unit,
                    updated_at=item.updated_at,
                )
                for item in episode.observations
            ),
        )
        for episode in episodes
    ]


def recompute_snapshot(db: Session, pet_id: int, window: str, as_of: datetime) -> BaselineSnapshot:
    normalized_as_of = utc(as_of)
    sources = load_sources(db, pet_id, window, normalized_as_of)
    fingerprint = source_fingerprint(pet_id, sources)
    existing = db.scalar(
        select(BaselineSnapshot).where(
            BaselineSnapshot.pet_id == pet_id,
            BaselineSnapshot.window == window,
            BaselineSnapshot.as_of == normalized_as_of,
            BaselineSnapshot.algorithm_version == ALGORITHM_VERSION,
            BaselineSnapshot.source_fingerprint == fingerprint,
        ).options(selectinload(BaselineSnapshot.evidences))
    )
    if existing is not None:
        if not existing.evidences:
            existing.evidences = _materialize_lineage(
                existing, build_lineage(window, normalized_as_of, sources)
            )
            db.flush()
        existing._is_stale = False
        return existing
    calculation = calculate_baseline(window, normalized_as_of, sources)
    snapshot = BaselineSnapshot(
        pet_id=pet_id,
        window=window,
        window_start=calculation.window_start,
        window_end=calculation.window_end,
        as_of=normalized_as_of,
        status=calculation.status,
        algorithm_version=ALGORITHM_VERSION,
        source_fingerprint=fingerprint,
        sample_count=calculation.sample_count,
        metrics_json=calculation.metrics,
    )
    db.add(snapshot)
    db.flush()
    snapshot.evidences = _materialize_lineage(
        snapshot, build_lineage(window, normalized_as_of, sources)
    )
    db.flush()
    snapshot._is_stale = False
    return snapshot


def mark_stale(db: Session, snapshot: BaselineSnapshot) -> BaselineSnapshot:
    sources = load_sources(db, snapshot.pet_id, snapshot.window, utc(snapshot.as_of))
    snapshot._is_stale = source_fingerprint(snapshot.pet_id, sources) != snapshot.source_fingerprint
    return snapshot


def get_snapshot(db: Session, snapshot_id: int) -> BaselineSnapshot | None:
    snapshot = db.scalar(
        select(BaselineSnapshot)
        .where(BaselineSnapshot.id == snapshot_id)
        .options(selectinload(BaselineSnapshot.evidences))
    )
    return None if snapshot is None else mark_stale(db, snapshot)


def get_latest_snapshot(db: Session, pet_id: int, window: str) -> BaselineSnapshot | None:
    snapshot = db.scalar(
        select(BaselineSnapshot)
        .where(BaselineSnapshot.pet_id == pet_id, BaselineSnapshot.window == window)
        .options(selectinload(BaselineSnapshot.evidences))
        .order_by(BaselineSnapshot.created_at.desc(), BaselineSnapshot.id.desc())
        .limit(1)
    )
    return None if snapshot is None else mark_stale(db, snapshot)
