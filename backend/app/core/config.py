import os
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Relapaw API"
    deployment_version: str = Field(default="development", validation_alias="RELAPAW_DEPLOYMENT_VERSION")
    environment: Literal["development", "test", "demo", "staging", "production"] = Field(default="development", validation_alias="RELAPAW_ENV")
    database_url: str = "sqlite:///./relapaw.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    ai_enabled: bool = Field(default=False, validation_alias="RELAPAW_AI_ENABLED")
    model_qualification: Literal["NOT_QUALIFIED", "QUALIFIED"] = Field(
        default="NOT_QUALIFIED", validation_alias="RELAPAW_MODEL_QUALIFICATION"
    )
    model_qualification_id: str | None = Field(default=None, validation_alias="RELAPAW_MODEL_QUALIFICATION_ID")
    medical_knowledge_version: str = Field(default="medical-safety/v1", validation_alias="RELAPAW_MEDICAL_KNOWLEDGE_VERSION")
    medical_review_status: Literal["PENDING", "APPROVED"] = Field(default="PENDING", validation_alias="RELAPAW_MEDICAL_REVIEW_STATUS")
    static_dir: Path | None = Field(default=None, validation_alias="RELAPAW_STATIC_DIR")
    media_dir: Path = Field(default=Path("./relapaw_media"), validation_alias="RELAPAW_MEDIA_DIR")
    media_max_bytes: int = Field(default=25 * 1024 * 1024, ge=1, le=100 * 1024 * 1024, validation_alias="RELAPAW_MEDIA_MAX_BYTES")
    media_total_bytes_per_user: int = Field(default=1024 * 1024 * 1024, ge=1, le=10 * 1024 * 1024 * 1024, validation_alias="RELAPAW_MEDIA_TOTAL_BYTES_PER_USER")
    media_max_video_seconds: int = Field(default=300, ge=1, le=3600, validation_alias="RELAPAW_MEDIA_MAX_VIDEO_SECONDS")
    avatar_max_bytes: int = Field(default=5 * 1024 * 1024, ge=1, le=10 * 1024 * 1024, validation_alias="RELAPAW_AVATAR_MAX_BYTES")
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "RELAPAW_OPENAI_API_KEY"),
    )
    openai_model: str | None = Field(default=None, validation_alias="RELAPAW_OPENAI_MODEL")
    openai_base_url: str | None = Field(default=None, validation_alias="RELAPAW_OPENAI_BASE_URL")
    model_provider: str = Field(default="openai", validation_alias="RELAPAW_MODEL_PROVIDER")
    openai_timeout_seconds: float = Field(default=20.0, gt=0, le=120, validation_alias="RELAPAW_OPENAI_TIMEOUT_SECONDS")
    openai_max_output_tokens: int = Field(default=1600, ge=256, le=8000, validation_alias="RELAPAW_OPENAI_MAX_OUTPUT_TOKENS")
    session_pepper: SecretStr = Field(default=SecretStr("development-only-change-me"), validation_alias="RELAPAW_SESSION_PEPPER")
    session_absolute_days: int = Field(default=30, ge=1, le=90, validation_alias="RELAPAW_SESSION_ABSOLUTE_DAYS")
    session_idle_days: int = Field(default=7, ge=1, le=30, validation_alias="RELAPAW_SESSION_IDLE_DAYS")
    local_invite_code: SecretStr | None = Field(default=None, validation_alias="RELAPAW_LOCAL_INVITE_CODE")
    email_identity_mode: Literal["local", "resend"] = Field(default="local", validation_alias="RELAPAW_EMAIL_IDENTITY_MODE")
    resend_api_key: SecretStr | None = Field(default=None, validation_alias="RESEND_API_KEY")
    resend_from_email: str | None = Field(default=None, validation_alias="RELAPAW_RESEND_FROM_EMAIL")
    email_test_recipient: str | None = Field(default=None, validation_alias="RELAPAW_TEST_RECIPIENT_EMAIL")
    resend_api_url: str = Field(default="https://api.resend.com/emails", validation_alias="RELAPAW_RESEND_API_URL")
    otp_expiry_minutes: int = Field(default=10, ge=1, le=30, validation_alias="RELAPAW_OTP_EXPIRY_MINUTES")
    otp_max_attempts: int = Field(default=5, ge=1, le=10, validation_alias="RELAPAW_OTP_MAX_ATTEMPTS")
    otp_resend_cooldown_seconds: int = Field(default=60, ge=30, le=600, validation_alias="RELAPAW_OTP_RESEND_COOLDOWN_SECONDS")
    otp_email_requests_per_hour: int = Field(default=5, ge=1, le=20, validation_alias="RELAPAW_OTP_EMAIL_REQUESTS_PER_HOUR")
    otp_source_requests_per_hour: int = Field(default=20, ge=1, le=100, validation_alias="RELAPAW_OTP_SOURCE_REQUESTS_PER_HOUR")
    otp_verify_attempts_per_15_minutes: int = Field(default=20, ge=5, le=100, validation_alias="RELAPAW_OTP_VERIFY_ATTEMPTS_PER_15_MINUTES")
    terms_version: str = Field(default="terms-draft-2026-10-20", validation_alias="RELAPAW_TERMS_VERSION")
    privacy_version: str = Field(default="privacy-draft-2026-10-20", validation_alias="RELAPAW_PRIVACY_VERSION")
    legal_documents_approved: bool = Field(default=False, validation_alias="RELAPAW_LEGAL_DOCUMENTS_APPROVED")
    account_deletion_grace_days: int = Field(default=7, ge=1, le=30, validation_alias="RELAPAW_ACCOUNT_DELETION_GRACE_DAYS")
    audit_retention_days: int = Field(default=365, ge=30, le=2555, validation_alias="RELAPAW_AUDIT_RETENTION_DAYS")

    @property
    def secure_cookies(self) -> bool:
        return self.environment in {"staging", "production"}

    @property
    def session_cookie_name(self) -> str:
        return "__Host-relapaw_session" if self.secure_cookies else "relapaw_dev_session"

    @model_validator(mode="after")
    def production_auth_fails_closed(self):
        if self.email_identity_mode == "resend" and (self.resend_api_key is None or not self.resend_from_email):
            raise ValueError("RESEND_API_KEY and RELAPAW_RESEND_FROM_EMAIL are required in Resend mode")
        if self.email_identity_mode == "resend" and self.resend_from_email:
            sender = self.resend_from_email.strip()
            if "@" not in sender or any(character in sender for character in "\r\n"):
                raise ValueError("RELAPAW_RESEND_FROM_EMAIL must be a valid sender address")
        if self.model_qualification == "QUALIFIED" and not self.model_qualification_id:
            raise ValueError("RELAPAW_MODEL_QUALIFICATION_ID is required for a qualified model")
        if self.model_qualification == "QUALIFIED":
            from app.domain.educational_knowledge import KNOWLEDGE_SET
            from app.domain.model_qualification import repository_qualification_matches

            configured_base_url = self.openai_base_url or "https://api.openai.com/v1"
            if not repository_qualification_matches(
                self.model_qualification_id,
                provider=self.model_provider,
                model=self.openai_model or "",
                base_url=configured_base_url,
                knowledge_set_version=KNOWLEDGE_SET["version"],
            ):
                raise ValueError("Qualified model configuration must match an approved in-repository qualification record")
        if self.environment in {"staging", "production"}:
            if self.email_identity_mode != "resend":
                raise ValueError("Resend email identity mode is required in staging and production")
            if self.resend_api_url != "https://api.resend.com/emails":
                raise ValueError("Staging and production must use the official Resend HTTPS endpoint")
            if self.email_test_recipient is not None:
                raise ValueError("RELAPAW_TEST_RECIPIENT_EMAIL is local verification configuration only")
            if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
                raise ValueError("PostgreSQL is required in staging and production")
            if not self.cors_origins or any(
                not origin.startswith("https://") or "localhost" in origin or "127.0.0.1" in origin
                for origin in self.cors_origins
            ):
                raise ValueError("Staging and production CORS origins must be explicit HTTPS origins")
            if self.deployment_version == "development":
                raise ValueError("RELAPAW_DEPLOYMENT_VERSION must identify the deployed release")
            pepper = self.session_pepper.get_secret_value()
            if pepper == "development-only-change-me" or len(pepper.strip()) < 32:
                raise ValueError("RELAPAW_SESSION_PEPPER must be an explicit secret of at least 32 characters")
            if self.local_invite_code is not None:
                raise ValueError("RELAPAW_LOCAL_INVITE_CODE is forbidden outside local environments")
            if not self.legal_documents_approved or "draft" in self.terms_version or "draft" in self.privacy_version:
                raise ValueError("Approved non-draft Terms and Privacy versions are required")
            from app.domain.medical_safety import MEDICAL_SAFETY_MANIFEST

            review = MEDICAL_SAFETY_MANIFEST["review"]
            if (
                self.medical_review_status != "APPROVED"
                or self.medical_knowledge_version != MEDICAL_SAFETY_MANIFEST["version"]
                or MEDICAL_SAFETY_MANIFEST["status"] != "APPROVED"
                or any(not review.get(field) for field in (
                    "reviewer_name", "reviewer_credential", "reviewed_at", "approval_reference"
                ))
            ):
                raise ValueError("Veterinarian-approved medical safety content is required")
            if self.ai_enabled and self.model_qualification != "QUALIFIED":
                raise ValueError("AI cannot be enabled without a qualified model")
        return self

    model_config = SettingsConfigDict(env_prefix="RELAPAW_", env_file=".env")


settings = Settings(
    _env_file=None
    if os.getenv("RELAPAW_ENV") == "test" or os.getenv("RELAPAW_DISABLE_DOTENV") == "1"
    else ".env"
)
