from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.analysis import AdapterDescriptor
from app.schemas.common import ORMModel


GuidanceMode = Literal["RECORD_REVIEW", "RECENT_CHANGE_COMPARISON", "VET_TIMELINE"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GuidanceRunCreate(StrictModel):
    request_id: str = Field(min_length=1, max_length=100)
    mode: GuidanceMode = "RECORD_REVIEW"


class GuidanceRecordInput(StrictModel):
    episode_id: int
    happened_at: datetime
    raw_owner_input: str
    observations: list[str]
    owner_interpretations: list[str]
    safety_status: str


class GuidanceKnowledgeInput(StrictModel):
    id: str
    version: str
    citation_id: str
    title: str
    summary: str
    source_title: str
    source_locator: str


class AssistantGuidanceInput(StrictModel):
    contract_version: Literal["assistant-guidance-input/v1"] = "assistant-guidance-input/v1"
    mode: GuidanceMode
    pet_id: int
    species: str
    current_record: GuidanceRecordInput
    recent_records: list[GuidanceRecordInput]
    recent_records_truncated: bool
    controlled_knowledge: list[GuidanceKnowledgeInput]


class GuidanceCitation(StrictModel):
    citation_id: str
    knowledge_id: str
    knowledge_version: str
    supports_section: Literal["possibly_relevant_background", "continue_observing", "contact_vet_when"]
    item_index: int = Field(ge=0)


class GuidanceRecordSource(StrictModel):
    section: Literal["records_show", "owner_interpretation"]
    item_index: int = Field(ge=0)
    episode_ids: list[int] = Field(min_length=1)


class AssistantGuidanceOutput(StrictModel):
    contract_version: Literal["assistant-guidance-output/v4"] = "assistant-guidance-output/v4"
    records_show: list[str] = Field(min_length=1)
    owner_interpretation: list[str]
    possibly_relevant_background: list[str]
    cannot_determine: list[str] = Field(min_length=1)
    continue_observing: list[str]
    contact_vet_when: list[str] = Field(min_length=1)
    sources_used: list[GuidanceCitation]
    record_sources: list[GuidanceRecordSource]


class AssistantGuidanceDescriptor(AdapterDescriptor):
    input_contract_version: str = "assistant-guidance-input/v1"
    output_contract_version: str = "assistant-guidance-output/v4"


class AssistantGuidanceRunRead(ORMModel):
    id: int
    episode_id: int
    request_id: str
    mode: GuidanceMode
    status: Literal["RUNNING", "COMPLETED", "FAILED", "BLOCKED_BY_SAFETY"]
    adapter_name: str
    model_provider: str
    model_name: str
    model_version: str
    prompt_contract_version: str
    input_contract_version: str
    output_contract_version: str
    input_snapshot: dict[str, Any]
    knowledge_snapshot: dict[str, Any]
    normalized_output: dict[str, Any] | None = None
    error_code: str | None = None
    source_episode_updated_at: datetime
    created_at: datetime
    completed_at: datetime | None = None
    is_stale: bool

    @field_validator("source_episode_updated_at", "created_at", "completed_at")
    @classmethod
    def database_datetimes_are_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
