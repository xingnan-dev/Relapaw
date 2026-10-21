from typing import Literal

from pydantic import BaseModel


class CapabilitiesRead(BaseModel):
    environment: str
    synthetic_data: bool
    dataset_version: str | None = None
    ai_analysis_enabled: bool
    model_qualification: Literal["NOT_QUALIFIED", "QUALIFIED"]
    model_qualification_id: str | None = None
    medical_knowledge_version: str
    medical_review_status: Literal["PENDING", "APPROVED"]
