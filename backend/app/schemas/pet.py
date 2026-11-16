from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel


class PetBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    species: str = Field(min_length=1, max_length=50)
    breed: str | None = None
    birth_date: date | None = None
    approximate_age: str | None = None
    sex: str | None = None
    neutered: bool | None = None
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    known_conditions: list[str] | None = None
    medications: list[str] | None = None
    allergies: list[str] | None = None
    living_environment: str | None = Field(default=None, max_length=4000)
    veterinarian_confirmed_facts: list[dict[str, str]] | None = None
    owner_observations: dict[str, str] | None = None

    @model_validator(mode="after")
    def age_is_not_duplicated(self):
        if self.birth_date and self.approximate_age:
            raise ValueError("Provide birth_date or approximate_age, not both")
        return self


class PetCreate(PetBase):
    pass


class PetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    species: str | None = Field(default=None, min_length=1, max_length=50)
    breed: str | None = None
    birth_date: date | None = None
    approximate_age: str | None = None
    sex: str | None = None
    neutered: bool | None = None
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    known_conditions: list[str] | None = None
    medications: list[str] | None = None
    allergies: list[str] | None = None
    living_environment: str | None = Field(default=None, max_length=4000)
    veterinarian_confirmed_facts: list[dict[str, str]] | None = None
    owner_observations: dict[str, str] | None = None
    archived: bool | None = None

    @model_validator(mode="after")
    def age_is_not_duplicated(self):
        if self.birth_date and self.approximate_age:
            raise ValueError("Provide birth_date or approximate_age, not both")
        return self


class PetAvatarRead(ORMModel):
    id: int
    pet_id: int
    original_filename: str
    media_type: str
    byte_size: int
    sha256: str
    created_at: datetime
    updated_at: datetime


class PetRead(PetBase, ORMModel):
    id: int
    created_at: datetime
    archived_at: datetime | None = None
    avatar: PetAvatarRead | None = None
