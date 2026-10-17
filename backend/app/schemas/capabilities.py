from typing import Literal

from pydantic import BaseModel


class CapabilitiesRead(BaseModel):
    environment: str
    synthetic_data: bool
    dataset_version: str | None = None
    ai_analysis_enabled: bool
    model_qualification: Literal["NOT_QUALIFIED"] = "NOT_QUALIFIED"
