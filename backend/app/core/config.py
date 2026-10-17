from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Relapaw API"
    environment: Literal["development", "test", "demo"] = Field(default="development", validation_alias="RELAPAW_ENV")
    database_url: str = "sqlite:///./relapaw.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    ai_enabled: bool = Field(default=False, validation_alias="RELAPAW_AI_ENABLED")
    static_dir: Path | None = Field(default=None, validation_alias="RELAPAW_STATIC_DIR")
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "RELAPAW_OPENAI_API_KEY"),
    )
    openai_model: str | None = Field(default=None, validation_alias="RELAPAW_OPENAI_MODEL")
    openai_base_url: str | None = Field(default=None, validation_alias="RELAPAW_OPENAI_BASE_URL")
    model_provider: str = Field(default="openai", validation_alias="RELAPAW_MODEL_PROVIDER")
    openai_timeout_seconds: float = Field(default=20.0, gt=0, le=120, validation_alias="RELAPAW_OPENAI_TIMEOUT_SECONDS")
    openai_max_output_tokens: int = Field(default=1600, ge=256, le=8000, validation_alias="RELAPAW_OPENAI_MAX_OUTPUT_TOKENS")

    model_config = SettingsConfigDict(env_prefix="RELAPAW_", env_file=".env")


settings = Settings()
