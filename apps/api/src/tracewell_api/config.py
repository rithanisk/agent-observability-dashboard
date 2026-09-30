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
    self_otlp_url: str = "http://127.0.0.1:8000/v1/traces"
    soclaas_base_url: str = Field(
        default="https://soclaas-api.comp.nus.edu.sg/v1",
        validation_alias="SOCLAAS_BASE_URL",
    )
    soclaas_model: str = Field(default="qwen3.5:9b", validation_alias="SOCLAAS_MODEL")
    soclaas_api_key: str = Field(default="", validation_alias="SOCLAAS_API_KEY")

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
