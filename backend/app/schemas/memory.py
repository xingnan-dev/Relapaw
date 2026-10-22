from datetime import datetime, timezone

from typing import Literal

from pydantic import Field, field_validator

from app.domain.enums import MemoryCandidateState, MemoryDecisionType
from app.schemas.analysis import StrictModel
from app.schemas.common import ORMModel


class MemoryDecisionCreate(StrictModel):
    request_id: str = Field(min_length=1, max_length=100)
    decision: MemoryDecisionType
    note: str | None = Field(default=None, max_length=2000)


class ManualMemoryCreate(StrictModel):
    category: Literal["ROUTINE", "PREFERENCE", "TRIGGER", "COMFORT", "HEALTH_CONTEXT", "OTHER"]
    statement: str = Field(min_length=1, max_length=2000)

    @field_validator("statement")
    @classmethod
    def statement_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("statement must contain non-whitespace text")
        return value


class ManualMemoryUpdate(ManualMemoryCreate):
    pass


class MemoryRevisionRead(ORMModel):
    id: int
    candidate_id: int
    revision_number: int
    category: str
    statement: str
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def database_datetime_is_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class MemoryDecisionRead(ORMModel):
    id: int
    candidate_id: int
    request_id: str
    decision: MemoryDecisionType
    note: str | None = None
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def database_datetime_is_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class MemoryCandidateRead(ORMModel):
    id: int
    pet_id: int
    claim_id: int | None
    source_type: Literal["CLAIM", "MANUAL"]
    claim_snapshot: dict
    evidence_snapshot: list[dict]
    uncertainty_snapshot: list[dict]
    model_snapshot: dict
    source_episode_updated_at: datetime | None
    created_at: datetime
    is_stale: bool
    state: MemoryCandidateState
    decisions: list[MemoryDecisionRead] = Field(default_factory=list)
    revisions: list[MemoryRevisionRead] = Field(default_factory=list)

    @field_validator("source_episode_updated_at", "created_at")
    @classmethod
    def database_datetimes_are_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
