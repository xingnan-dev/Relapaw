from datetime import date
from typing import Literal
from pydantic import BaseModel


class KnowledgeSource(BaseModel):
    title: str
    version: str
    locator: str
    url: str | None = None


class KnowledgeEntry(BaseModel):
    id: str
    version: str
    species: list[str]
    title: str
    summary: str
    topics: list[str]
    source: KnowledgeSource
    published_at: date
    review_status: Literal["DRAFT", "APPROVED", "WITHDRAWN"]
    reviewed_at: date | None = None
    withdrawn_at: date | None = None
    scope: Literal["recording_method_only"]


class KnowledgeSetRead(BaseModel):
    version: str
    review_status: Literal["DRAFT", "APPROVED", "WITHDRAWN"]
    review_note: str
    entries: list[KnowledgeEntry]


class EducationalGuidanceRead(BaseModel):
    status: Literal["EDUCATIONAL_ONLY"]
    knowledge_version: str
    review_status: Literal["DRAFT", "APPROVED", "WITHDRAWN"]
    review_note: str
    fact_summary: list[str]
    entries: list[KnowledgeEntry]
    limitations: list[str]
