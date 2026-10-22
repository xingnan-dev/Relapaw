from datetime import datetime, timezone
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.schemas.analysis import StrictModel
from app.schemas.common import ORMModel
from app.schemas.time import require_aware_utc

RelationshipKind = Literal["OWNER_PET", "PET_PET"]
RelationshipObservationType = Literal[
    "OWNER_INTERACTION", "SHARED_REST", "INTERACTION", "AVOIDANCE", "CONFLICT", "RESOURCE_SHARING", "OTHER"
]


class RelationshipEventCreate(StrictModel):
    relationship_kind: RelationshipKind
    participant_pet_ids: list[int] = Field(min_length=1, max_length=2)
    happened_at: datetime
    observation_type: RelationshipObservationType
    observation_text: str = Field(min_length=1, max_length=4000)
    owner_interpretation: str | None = Field(default=None, max_length=4000)
    source_episode_id: int | None = None

    @field_validator("happened_at")
    @classmethod
    def happened_at_is_aware(cls, value: datetime) -> datetime:
        return require_aware_utc(value)  # type: ignore[return-value]

    @field_validator("observation_text")
    @classmethod
    def observation_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("observation_text must contain non-whitespace text")
        return value

    @field_validator("owner_interpretation")
    @classmethod
    def interpretation_is_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("owner_interpretation must contain non-whitespace text")
        return value

    @model_validator(mode="after")
    def participant_shape_matches_kind(self):
        unique_ids = list(dict.fromkeys(self.participant_pet_ids))
        if len(unique_ids) != len(self.participant_pet_ids):
            raise ValueError("participant_pet_ids must be unique")
        expected = 1 if self.relationship_kind == "OWNER_PET" else 2
        if len(unique_ids) != expected:
            raise ValueError(f"{self.relationship_kind} requires exactly {expected} pet participant(s)")
        if self.relationship_kind == "OWNER_PET" and self.observation_type not in {"OWNER_INTERACTION", "OTHER"}:
            raise ValueError("OWNER_PET requires OWNER_INTERACTION or OTHER observation type")
        if self.relationship_kind == "PET_PET" and self.observation_type == "OWNER_INTERACTION":
            raise ValueError("PET_PET cannot use OWNER_INTERACTION observation type")
        return self


class RelationshipEventUpdate(RelationshipEventCreate):
    pass


class RelationshipParticipantRead(ORMModel):
    id: int
    pet_id: int


class RelationshipInterpretationRead(ORMModel):
    id: int
    interpretation: str
    created_at: datetime


class RelationshipRevisionRead(ORMModel):
    id: int
    revision_number: int
    relationship_kind: RelationshipKind
    happened_at: datetime
    participant_pet_ids: list[int]
    observation_type: str
    observation_text: str
    owner_interpretation: str | None
    source_episode_id: int | None
    created_at: datetime


class RelationshipEventRead(ORMModel):
    id: int
    owner_user_id: str
    relationship_kind: RelationshipKind
    happened_at: datetime
    observation_type: RelationshipObservationType
    observation_text: str
    source_episode_id: int | None
    created_at: datetime
    updated_at: datetime
    current_owner_interpretation: str | None
    participants: list[RelationshipParticipantRead]
    interpretations: list[RelationshipInterpretationRead]
    revisions: list[RelationshipRevisionRead]

    @field_validator("happened_at", "created_at", "updated_at")
    @classmethod
    def database_datetime_is_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
