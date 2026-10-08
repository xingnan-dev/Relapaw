from pydantic import BaseModel

from app.schemas.common import ORMModel


class OwnerProfileUpsert(BaseModel):
    interaction_preference: str | None = None
    observation_preference: str | None = None
    response_preference: str | None = None
    explanation_preference: str | None = None


class OwnerProfileRead(OwnerProfileUpsert, ORMModel):
    id: int

