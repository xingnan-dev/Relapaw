from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.common import ORMModel

class MediaAttachmentRead(ORMModel):
    id: int
    episode_id: int
    original_filename: str
    media_type: str
    byte_size: int
    sha256: str
    status: str
    observable_facts: str | None
    created_at: datetime

class MediaFactsUpdate(BaseModel):
    observable_facts: str | None = Field(default=None, max_length=5000)
