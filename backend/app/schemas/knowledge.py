from typing import Literal
from pydantic import BaseModel


class KnowledgeSource(BaseModel):
    title: str
    version: str
    locator: str
    url: str | None = None


class KnowledgeEntry(BaseModel):
    id: str
    species: list[str]
    title: str
    summary: str
    topics: list[str]
    source: KnowledgeSource
    review_status: Literal["UNREVIEWED_EXAMPLE"] = "UNREVIEWED_EXAMPLE"


class KnowledgeSetRead(BaseModel):
    version: str
    review_status: Literal["UNREVIEWED_EXAMPLE"]
    review_note: str
    entries: list[KnowledgeEntry]


class EducationalGuidanceRead(BaseModel):
    status: Literal["EDUCATIONAL_ONLY"]
    knowledge_version: str
    review_status: Literal["UNREVIEWED_EXAMPLE"]
    review_note: str
    fact_summary: list[str]
    entries: list[KnowledgeEntry]
    limitations: list[str]
