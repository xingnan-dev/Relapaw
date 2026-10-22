from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator, field_validator

from app.domain.enums import LifeEventType, ObservationPlanStatus, VeterinaryEscalationStatus
from app.schemas.common import ORMModel
from app.schemas.time import require_aware_utc


class PetBaselineUpsert(BaseModel):
    social_behavior: dict[str, Any] | None = None
    activity_pattern: dict[str, Any] | None = None
    feeding_pattern: dict[str, Any] | None = None
    resting_pattern: dict[str, Any] | None = None
    handling_preference: dict[str, Any] | None = None
    hiding_pattern: dict[str, Any] | None = None


class PetBaselineRead(PetBaselineUpsert, ORMModel):
    id: int
    pet_id: int


class LifeEventCreate(BaseModel):
    event_type: LifeEventType
    happened_at: datetime
    description: str | None = None

    @field_validator("happened_at")
    @classmethod
    def happened_at_is_aware(cls, value: datetime) -> datetime:
        return require_aware_utc(value)  # type: ignore[return-value]


class LifeEventUpdate(BaseModel):
    event_type: LifeEventType | None = None
    happened_at: datetime | None = None
    description: str | None = None

    @field_validator("happened_at")
    @classmethod
    def happened_at_is_aware(cls, value: datetime | None) -> datetime | None:
        return require_aware_utc(value)

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self):
        provided = self.model_fields_set
        if "event_type" in provided and self.event_type is None:
            raise ValueError("event_type cannot be null")
        if "happened_at" in provided and self.happened_at is None:
            raise ValueError("happened_at cannot be null")
        return self


class LifeEventRead(ORMModel):
    id: int
    pet_id: int
    event_type: LifeEventType
    happened_at: datetime
    description: str | None = None

    @field_validator("happened_at")
    @classmethod
    def database_datetime_is_utc(cls, value: datetime) -> datetime:
        from datetime import timezone
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class ObservationPlanItemCreate(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    description: str | None = None
    is_required: bool = True


class ObservationPlanItemRead(ORMModel):
    id: int
    plan_id: int
    label: str
    description: str | None = None
    sort_order: int
    is_required: bool
    created_at: datetime


class ObservationPlanCreate(BaseModel):
    status: ObservationPlanStatus = ObservationPlanStatus.DRAFT
    start_at: datetime | None = None
    end_at: datetime | None = None
    goal: str = Field(min_length=1)
    items_to_observe: list[dict[str, Any]] = Field(default_factory=list)
    items: list[ObservationPlanItemCreate] = Field(default_factory=list)

    @field_validator("start_at", "end_at")
    @classmethod
    def dates_are_aware(cls, value: datetime | None) -> datetime | None:
        return require_aware_utc(value)

    @model_validator(mode="after")
    def date_order(self):
        if self.start_at and self.end_at and self.end_at < self.start_at:
            raise ValueError("end_at must be on or after start_at")
        return self


class ObservationPlanUpdate(BaseModel):
    status: ObservationPlanStatus | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    goal: str | None = Field(default=None, min_length=1)
    items_to_observe: list[dict[str, Any]] | None = None
    items: list[ObservationPlanItemCreate] | None = None

    @field_validator("start_at", "end_at")
    @classmethod
    def dates_are_aware(cls, value: datetime | None) -> datetime | None:
        return require_aware_utc(value)


class ObservationPlanRead(ORMModel):
    id: int
    pet_id: int
    status: ObservationPlanStatus
    start_at: datetime | None = None
    end_at: datetime | None = None
    goal: str
    items_to_observe: list[dict[str, Any]] = Field(default_factory=list)
    items: list[ObservationPlanItemRead] = Field(default_factory=list)

    @field_validator("start_at", "end_at")
    @classmethod
    def database_datetimes_are_utc(cls, value: datetime | None) -> datetime | None:
        from datetime import timezone
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class VeterinaryEscalationCreate(BaseModel):
    reason: str = Field(min_length=1)
    status: VeterinaryEscalationStatus = VeterinaryEscalationStatus.OPEN
    vet_brief: str | None = None


class VeterinaryEscalationUpdate(BaseModel):
    reason: str | None = Field(default=None, min_length=1)
    status: VeterinaryEscalationStatus | None = None
    vet_brief: str | None = None


class VeterinaryEscalationRead(VeterinaryEscalationCreate, ORMModel):
    id: int
    episode_id: int
