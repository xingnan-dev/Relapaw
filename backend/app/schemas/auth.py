from pydantic import BaseModel, Field


class ChallengeRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class ChallengeVerify(ChallengeRequest):
    code: str = Field(min_length=1, max_length=200)


class SessionRead(BaseModel):
    user_id: str
    status: str
    consent_required: bool


class CsrfRead(BaseModel):
    csrf_token: str
