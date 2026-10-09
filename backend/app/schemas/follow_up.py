from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import FollowUpOutcome, FollowUpStatus
from app.schemas.common import ORMModel
from app.schemas.episode import ObservationCreate, OwnerInterpretationCreate, SafetyCheckCreate
from app.schemas.time import require_aware_utc


class FollowUpCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scheduled_at: datetime

    @field_validator("scheduled_at")
    @classmethod
    def scheduled_at_is_aware(cls, value: datetime) -> datetime:
        return require_aware_utc(value)  # type: ignore[return-value]


class FollowUpRead(ORMModel):
    id: int
    source_episode_id: int
    result_episode_id: int | None = None
    scheduled_at: datetime
    status: FollowUpStatus
    outcome: FollowUpOutcome | None = None
    created_at: datetime
    completed_at: datetime | None = None

    @field_validator("scheduled_at", "created_at", "completed_at")
    @classmethod
    def database_datetimes_are_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class FollowUpListItem(FollowUpRead):
    source_episode_type: str
    source_raw_owner_input: str
    source_happened_at: datetime
    timing_status: str

    @field_validator("source_happened_at")
    @classmethod
    def source_datetime_is_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class FollowUpComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome: FollowUpOutcome
    happened_at: datetime
    episode_type: str = Field(default="follow_up", min_length=1, max_length=100)
    raw_owner_input: str = Field(min_length=1)
    context: dict[str, Any] | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    frequency_count: int | None = Field(default=None, ge=1)
    intensity: int | None = Field(default=None, ge=1, le=5)
    location: str | None = Field(default=None, max_length=200)
    trigger_context: str | None = None
    observations: list[ObservationCreate] = Field(min_length=1)
    owner_interpretations: list[OwnerInterpretationCreate] = Field(default_factory=list)
    safety_check: SafetyCheckCreate

    @field_validator("happened_at")
    @classmethod
    def happened_at_is_aware(cls, value: datetime) -> datetime:
        return require_aware_utc(value)  # type: ignore[return-value]
