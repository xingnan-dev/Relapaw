from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.domain.enums import ObservationSourceType
from app.schemas.common import ORMModel
from app.schemas.time import require_aware_utc


class ObservationCreate(BaseModel):
    behavior_type: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    source_type: ObservationSourceType
    confidence: float | None = Field(default=None, ge=0, le=1)


class ObservationRead(ObservationCreate, ORMModel):
    id: int
    episode_id: int


class OwnerInterpretationCreate(BaseModel):
    interpretation: str = Field(min_length=1)


class OwnerInterpretationRead(OwnerInterpretationCreate, ORMModel):
    id: int
    episode_id: int


class EpisodeCreate(BaseModel):
    pet_id: int
    happened_at: datetime
    episode_type: str = Field(min_length=1, max_length=100)
    raw_owner_input: str = Field(min_length=1)
    context: dict[str, Any] | None = None

    @field_validator("happened_at")
    @classmethod
    def happened_at_is_aware(cls, value: datetime) -> datetime:
        return require_aware_utc(value)  # type: ignore[return-value]


class EpisodeRead(ORMModel):
    id: int
    pet_id: int
    happened_at: datetime
    episode_type: str
    raw_owner_input: str
    context: dict[str, Any] | None = None
    created_at: datetime
    observations: list[ObservationRead] = Field(default_factory=list)
    owner_interpretations: list[OwnerInterpretationRead] = Field(default_factory=list)

    @field_validator("happened_at", "created_at")
    @classmethod
    def database_datetimes_are_utc(cls, value: datetime) -> datetime:
        from datetime import timezone
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class TimelinePage(BaseModel):
    items: list[EpisodeRead]
    total: int
    page: int
    page_size: int
    has_more: bool
