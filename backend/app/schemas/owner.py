from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import ORMModel


class OwnerProfileUpsert(BaseModel):
    interaction_preference: str | None = None
    observation_preference: str | None = None
    response_preference: str | None = None
    explanation_preference: str | None = None
    living_together_since: date | None = None
    primary_caregiver: str | None = Field(default=None, max_length=200)
    household_members: list[str] | None = None
    daily_routine: str | None = Field(default=None, max_length=2000)
    pet_alone_hours: float | None = Field(default=None, ge=0, le=24)
    pet_care_experience: str | None = Field(default=None, max_length=2000)
    current_concerns: str | None = Field(default=None, max_length=4000)
    reminder_preference: str | None = Field(default=None, max_length=100)
    recording_capacity: str | None = Field(default=None, max_length=2000)
    household_context: dict[str, bool] | None = None
    caregiving_constraints: str | None = Field(default=None, max_length=4000)
    ai_context_enabled: bool = False
    ai_context_fields: list[str] | None = None

    @field_validator("household_members")
    @classmethod
    def household_members_are_bounded(cls, value):
        if value is not None and (len(value) > 20 or any(not item.strip() or len(item) > 100 for item in value)):
            raise ValueError("household_members must contain at most 20 short descriptions")
        return [item.strip() for item in value] if value is not None else None

    @model_validator(mode="after")
    def ai_consent_is_explicit(self):
        allowed = set(type(self).model_fields) - {"ai_context_enabled", "ai_context_fields"}
        selected = set(self.ai_context_fields or [])
        if not self.ai_context_enabled and selected:
            raise ValueError("AI context fields require explicit consent")
        if selected - allowed:
            raise ValueError("Unknown AI context field")
        return self


class OwnerProfileRead(OwnerProfileUpsert, ORMModel):
    id: int
    ai_context_consent_updated_at: datetime | None = None
