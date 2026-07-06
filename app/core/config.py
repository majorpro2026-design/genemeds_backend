from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

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
    database_url: str | None = "jdbc:postgresql://genemeds.cupgeqgu0vg9.us-east-1.rds.amazonaws.com:5432/genemeds"
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "genemeds"
    database_user: str = "postgres"
    database_password: str = "postgres"
    database_sslmode: str = "require"

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        if self.database_url:
            return self

        self.database_url = str(
            URL.create(
                "postgresql+psycopg",
                username=self.database_user,
                password=self.database_password,
                host=self.database_host,
                port=self.database_port,
                database=self.database_name,
                query={"sslmode": self.database_sslmode},
            )
        )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
