from pydantic import BaseModel

from app.domain.enums import SafetyStatus


class UnderstandResult(BaseModel):
    observations: list[str]
    owner_interpretations: list[str]
    historical_context: list[str]
    possible_explanations: list[str]
    uncertainty: list[str]
    safety_status: SafetyStatus
    next_steps: list[str]
