from datetime import datetime, timezone

from typing import Any

from pydantic import Field, field_validator

from app.domain.enums import BaselineSnapshotStatus, BaselineWindow
from app.schemas.analysis import StrictModel
from app.schemas.common import ORMModel


class BaselineRecompute(StrictModel):
    window: BaselineWindow
    as_of: datetime

    @field_validator("as_of")
    @classmethod
    def as_of_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("as_of must include a timezone offset")
        return value.astimezone(timezone.utc)


class BaselineSnapshotRead(ORMModel):
    id: int
    pet_id: int
    window: BaselineWindow
    window_start: datetime | None
    window_end: datetime
    as_of: datetime
    status: BaselineSnapshotStatus
    algorithm_version: str
    source_fingerprint: str
    sample_count: int
    metrics_json: list[dict]
    created_at: datetime
    is_stale: bool
    evidences: list["BaselineEvidenceRead"] = Field(default_factory=list)

    @field_validator("window_start", "window_end", "as_of", "created_at")
    @classmethod
    def database_datetimes_are_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class BaselineEvidenceRead(ORMModel):
    id: int
    snapshot_id: int
    episode_id: int | None
    observation_id: int | None
    source_type: str
    window_segment: str
    metric_key: str
    field_path: str
    value_snapshot: Any
    source_snapshot: dict[str, Any]
    observed_at: datetime
    source_updated_at: datetime
    created_at: datetime

    @field_validator("observed_at", "source_updated_at", "created_at")
    @classmethod
    def database_datetimes_are_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
