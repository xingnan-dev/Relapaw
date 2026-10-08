from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Relapaw API"
    database_url: str = "sqlite:///./relapaw.db"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_prefix="RELAPAW_", env_file=".env")


settings = Settings()

