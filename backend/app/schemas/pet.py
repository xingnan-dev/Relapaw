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
    archived: bool | None = None

    @model_validator(mode="after")
    def age_is_not_duplicated(self):
        if self.birth_date and self.approximate_age:
            raise ValueError("Provide birth_date or approximate_age, not both")
        return self


class PetRead(PetBase, ORMModel):
    id: int
    created_at: datetime
    archived_at: datetime | None = None
