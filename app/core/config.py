from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "GeneMeds"
    app_env: str = "development"
    app_debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str | None = None
    database_host: str | None = None
    database_port: int | None = None
    database_name: str | None = None
    database_user: str | None = None
    database_password: str | None = None
    database_sslmode: str = "require"


@lru_cache
def get_settings() -> Settings:
    return Settings()
