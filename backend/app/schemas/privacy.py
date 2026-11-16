from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ConsentCreate(BaseModel):
    terms_version: str
    privacy_version: str
    source: Literal["ONBOARDING", "VERSION_UPDATE"] = "ONBOARDING"
    affirm_adult_owner: bool


class PrivacyNoticeRead(BaseModel):
    terms_version: str
    privacy_version: str
    legal_review_status: Literal["PENDING", "APPROVED"]
    data_inventory_version: str


class AccountDeletionRequest(BaseModel):
    confirmation: Literal["DELETE MY ACCOUNT"]


class AccountDeletionRead(BaseModel):
    status: Literal["PENDING_DELETION"]
    deletion_due_at: datetime
