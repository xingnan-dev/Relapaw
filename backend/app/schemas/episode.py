from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import DangerSignal, EvidenceSourceType, ObservationSourceType, SafetyStatus, VeterinaryEscalationStatus
from app.schemas.common import ORMModel
from app.schemas.time import require_aware_utc


class ObservationCreate(BaseModel):
    behavior_type: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    source_type: ObservationSourceType
    confidence: float | None = Field(default=None, ge=0, le=1)
    measured_value: float | None = None
    unit: str | None = Field(default=None, max_length=50)


class ObservationRead(ObservationCreate, ORMModel):
    id: int
    episode_id: int
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def database_datetimes_are_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class OwnerInterpretationCreate(BaseModel):
    interpretation: str = Field(min_length=1)


class OwnerInterpretationRead(OwnerInterpretationCreate, ORMModel):
    id: int
    episode_id: int
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def database_datetimes_are_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class EpisodeCreate(BaseModel):
    pet_id: int
    happened_at: datetime
    episode_type: str = Field(min_length=1, max_length=100)
    raw_owner_input: str = Field(min_length=1)
    context: dict[str, Any] | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    frequency_count: int | None = Field(default=None, ge=1)
    intensity: int | None = Field(default=None, ge=1, le=5)
    location: str | None = Field(default=None, max_length=200)
    trigger_context: str | None = None

    @field_validator("happened_at")
    @classmethod
    def happened_at_is_aware(cls, value: datetime) -> datetime:
        return require_aware_utc(value)  # type: ignore[return-value]


class SafetyCheckCreate(BaseModel):
    result: SafetyStatus
    danger_signals: list[DangerSignal] = Field(default_factory=list)
    other_concern: str | None = None
    acknowledged_at: datetime

    @field_validator("acknowledged_at")
    @classmethod
    def acknowledged_at_is_aware(cls, value: datetime) -> datetime:
        return require_aware_utc(value)  # type: ignore[return-value]

    @model_validator(mode="after")
    def result_matches_manual_signals(self):
        has_concern = bool(self.danger_signals or (self.other_concern and self.other_concern.strip()))
        if self.result == SafetyStatus.NORMAL and has_concern:
            raise ValueError("NORMAL safety result cannot include danger signals")
        if self.result == SafetyStatus.ESCALATE_TO_VET and not has_concern:
            raise ValueError("ESCALATE_TO_VET requires a selected signal or other concern")
        return self


class SafetyCheckRead(ORMModel):
    id: int
    episode_id: int
    result: SafetyStatus
    danger_signals: list[DangerSignal] = Field(default_factory=list)
    other_concern: str | None = None
    acknowledged_at: datetime
    created_at: datetime

    @field_validator("acknowledged_at", "created_at")
    @classmethod
    def database_datetimes_are_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class EvidenceReferenceRead(ORMModel):
    id: int
    episode_id: int
    source_type: EvidenceSourceType
    source_id: int | None = None
    field_path: str
    observed_at: datetime
    recorded_at: datetime
    created_at: datetime

    @field_validator("observed_at", "recorded_at", "created_at")
    @classmethod
    def database_datetimes_are_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class EpisodePlanLinkRead(ORMModel):
    id: int
    episode_id: int
    plan_id: int
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def database_datetime_is_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class CompleteEpisodeCreate(EpisodeCreate):
    observations: list[ObservationCreate] = Field(min_length=1)
    owner_interpretations: list[OwnerInterpretationCreate] = Field(default_factory=list)
    safety_check: SafetyCheckCreate
    plan_id: int | None = None


class EpisodeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    happened_at: datetime
    episode_type: str = Field(min_length=1, max_length=100)
    raw_owner_input: str = Field(min_length=1)
    context: dict[str, Any] | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    frequency_count: int | None = Field(default=None, ge=1)
    intensity: int | None = Field(default=None, ge=1, le=5)
    location: str | None = Field(default=None, max_length=200)
    trigger_context: str | None = None
    observations: list[ObservationCreate] = Field(min_length=1)
    owner_interpretations: list[OwnerInterpretationCreate] = Field(default_factory=list)

    @field_validator("happened_at")
    @classmethod
    def happened_at_is_aware(cls, value: datetime) -> datetime:
        return require_aware_utc(value)  # type: ignore[return-value]


class VeterinaryEscalationRead(ORMModel):
    id: int
    episode_id: int
    reason: str
    status: VeterinaryEscalationStatus
    vet_brief: str | None = None


class FollowUpLinkRead(ORMModel):
    id: int
    source_episode_id: int
    result_episode_id: int | None = None
    scheduled_at: datetime
    status: str
    outcome: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    @field_validator("scheduled_at", "created_at", "completed_at")
    @classmethod
    def database_datetimes_are_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class EpisodeRead(ORMModel):
    id: int
    pet_id: int
    happened_at: datetime
    episode_type: str
    raw_owner_input: str
    context: dict[str, Any] | None = None
    duration_seconds: int | None = None
    frequency_count: int | None = None
    intensity: int | None = None
    location: str | None = None
    trigger_context: str | None = None
    created_at: datetime
    updated_at: datetime
    observations: list[ObservationRead] = Field(default_factory=list)
    owner_interpretations: list[OwnerInterpretationRead] = Field(default_factory=list)
    safety_check: SafetyCheckRead | None = None
    evidence_references: list[EvidenceReferenceRead] = Field(default_factory=list)
    plan_links: list[EpisodePlanLinkRead] = Field(default_factory=list)
    veterinary_escalations: list[VeterinaryEscalationRead] = Field(default_factory=list)
    scheduled_follow_ups: list[FollowUpLinkRead] = Field(default_factory=list)
    result_of_follow_up: FollowUpLinkRead | None = None

    @field_validator("happened_at", "created_at", "updated_at")
    @classmethod
    def database_datetimes_are_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class TimelinePage(BaseModel):
    items: list[EpisodeRead]
    total: int
    page: int
    page_size: int
    has_more: bool
