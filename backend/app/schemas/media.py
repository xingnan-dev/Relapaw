from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field
from app.schemas.common import ORMModel

class MediaAttachmentRead(ORMModel):
    id: int
    pet_id: int
    episode_id: int | None
    life_event_id: int | None
    relationship_event_id: int | None
    original_filename: str
    media_type: str
    byte_size: int
    sha256: str
    status: str
    observable_facts: str | None
    captured_at: datetime | None
    owner_caption: str | None
    duration_seconds: int | None
    ai_candidate_observation: str | None
    ai_candidate_status: str
    created_at: datetime
    updated_at: datetime
    revisions: list["MediaRevisionRead"]

class MediaFactsUpdate(BaseModel):
    observable_facts: str | None = Field(default=None, max_length=5000)

class MediaMetadataUpdate(BaseModel):
    captured_at: datetime | None = None
    owner_caption: str | None = Field(default=None, max_length=5000)
    change_summary: str | None = Field(default=None, max_length=500)

class MediaCandidateUpdate(BaseModel):
    action: Literal["CONFIRM", "REJECT", "WITHDRAW"]
    change_summary: str | None = Field(default=None, max_length=500)

class MediaRevisionRead(ORMModel):
    id: int
    revision_number: int
    captured_at: datetime | None
    owner_caption: str | None
    ai_candidate_observation: str | None
    ai_candidate_status: str
    change_summary: str | None
    created_at: datetime

MediaAttachmentRead.model_rebuild()
