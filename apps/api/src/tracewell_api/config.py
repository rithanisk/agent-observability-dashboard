from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_prefix="TRACEWELL_",
        extra="ignore",
    )

    env: str = "development"
    database_url: str = Field(
        default="postgresql+asyncpg://tracewell:tracewell@localhost:5432/tracewell",
        validation_alias="DATABASE_URL",
    )
    ingest_token: str = ""
    auto_create_schema: bool = False
    cors_origins: str = "http://localhost:3000"

    @property
    def async_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        return self.database_url

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
