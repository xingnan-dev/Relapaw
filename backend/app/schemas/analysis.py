from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import (
    AnalysisRunStatus,
    ClaimConfidence,
    ClaimStatus,
    ConfirmationDecision,
    EvidenceRole,
    SafetyStatus,
    UncertaintyKind,
)
from app.schemas.common import ORMModel


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnalysisRunCreate(StrictModel):
    request_id: str = Field(min_length=1, max_length=100)


class AnalysisEvidenceInput(StrictModel):
    key: str
    source_type: str
    source_id: int | None = None
    field_path: str
    observed_at: datetime
    recorded_at: datetime
    excerpt: str | None = None


class UnderstandingObservationInput(StrictModel):
    id: int
    description: str
    behavior_type: str
    measured_value: float | None = None
    unit: str | None = None


class UnderstandingInterpretationInput(StrictModel):
    id: int
    interpretation: str


class UnderstandingInput(StrictModel):
    contract_version: Literal["understanding-input/v1"] = "understanding-input/v1"
    episode_id: int
    pet_id: int
    raw_owner_input: str
    observations: list[UnderstandingObservationInput]
    owner_interpretations: list[UnderstandingInterpretationInput]
    safety_status: SafetyStatus
    evidence: list[AnalysisEvidenceInput]


class ProposedEvidenceReference(StrictModel):
    evidence_key: str
    role: EvidenceRole


class ProposedUncertainty(StrictModel):
    kind: UncertaintyKind
    description: str = Field(min_length=1)


class ProposedClaim(StrictModel):
    claim_type: str = Field(min_length=1, max_length=100)
    statement: str = Field(min_length=1)
    confidence_label: ClaimConfidence
    evidence: list[ProposedEvidenceReference] = Field(min_length=1)
    uncertainties: list[ProposedUncertainty] = Field(min_length=1)


class UnderstandingOutput(StrictModel):
    contract_version: Literal["understanding-output/v1"] = "understanding-output/v1"
    claims: list[ProposedClaim]


class AdapterDescriptor(StrictModel):
    adapter_name: str
    model_provider: str
    model_name: str
    model_version: str
    prompt_contract_version: str
    input_contract_version: str = "understanding-input/v1"
    output_contract_version: str = "understanding-output/v1"


class ConfirmationCreate(StrictModel):
    decision: ConfirmationDecision
    note: str | None = Field(default=None, max_length=2000)


class ConfirmationRead(ORMModel):
    id: int
    claim_id: int
    decision: ConfirmationDecision
    note: str | None = None
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def database_datetime_is_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class UncertaintyRead(ORMModel):
    id: int
    claim_id: int
    kind: UncertaintyKind
    description: str
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def database_datetime_is_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class ClaimEvidenceReferenceRead(ORMModel):
    id: int
    claim_id: int
    evidence_reference_id: int | None = None
    source_type: str
    source_id: int | None = None
    field_path: str
    observed_at: datetime
    recorded_at: datetime
    excerpt: str | None = None
    role: EvidenceRole
    created_at: datetime

    @field_validator("observed_at", "recorded_at", "created_at")
    @classmethod
    def database_datetimes_are_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class ClaimRead(ORMModel):
    id: int
    analysis_run_id: int
    claim_type: str
    statement: str
    confidence_label: ClaimConfidence
    status: ClaimStatus
    created_at: datetime
    evidence_references: list[ClaimEvidenceReferenceRead] = Field(default_factory=list)
    uncertainties: list[UncertaintyRead] = Field(default_factory=list)
    confirmations: list[ConfirmationRead] = Field(default_factory=list)

    @field_validator("created_at")
    @classmethod
    def database_datetime_is_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class AnalysisRunRead(ORMModel):
    id: int
    episode_id: int
    request_id: str
    status: AnalysisRunStatus
    adapter_name: str
    model_provider: str
    model_name: str
    model_version: str
    prompt_contract_version: str
    input_contract_version: str
    output_contract_version: str
    input_snapshot: dict[str, Any]
    normalized_output: dict[str, Any] | None = None
    error_code: str | None = None
    source_episode_updated_at: datetime
    created_at: datetime
    completed_at: datetime | None = None
    is_stale: bool
    claims: list[ClaimRead] = Field(default_factory=list)

    @field_validator("source_episode_updated_at", "created_at", "completed_at")
    @classmethod
    def database_datetimes_are_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
