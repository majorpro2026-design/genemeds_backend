from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "GeneMeds"
    app_env: str = "development"
    app_debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/generx"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

