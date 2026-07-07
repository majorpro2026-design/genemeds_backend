from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

logger = logging.getLogger("genemeds.database")


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


@dataclass(frozen=True)
class ResolvedDatabaseConfig:
    url: str
    host: str
    port: int
    database: str
    username: str


def _missing_fields_message(fields: list[str]) -> str:
    fields_text = ", ".join(fields)
    return (
        "Database configuration is incomplete. "
        f"Provide DATABASE_URL or the following environment variables: {fields_text}."
    )


def _resolve_database_config() -> ResolvedDatabaseConfig:
    settings = get_settings()
    raw_url = settings.database_url.strip() if settings.database_url else None

    if raw_url:
        if raw_url.startswith("jdbc:postgresql://"):
            parsed = urlparse(raw_url.removeprefix("jdbc:"))
            host = settings.database_host or parsed.hostname
            port = settings.database_port or parsed.port
            database = settings.database_name or parsed.path.lstrip("/") or None
            username = settings.database_user
            password = settings.database_password
        else:
            parsed_url = make_url(raw_url)
            host = settings.database_host or parsed_url.host
            port = settings.database_port or parsed_url.port
            database = settings.database_name or parsed_url.database
            username = settings.database_user or parsed_url.username
            password = settings.database_password or parsed_url.password

        missing: list[str] = []
        if not host:
            missing.append("DATABASE_HOST")
        if not port:
            missing.append("DATABASE_PORT")
        if not database:
            missing.append("DATABASE_NAME")
        if not username:
            missing.append("DATABASE_USER")
        if not password:
            missing.append("DATABASE_PASSWORD")
        if missing:
            raise RuntimeError(_missing_fields_message(missing))

        resolved_url = str(
            URL.create(
                "postgresql+psycopg",
                username=username,
                password=password,
                host=host,
                port=int(port),
                database=database,
                query={"sslmode": settings.database_sslmode},
            )
        )
        return ResolvedDatabaseConfig(
            url=resolved_url,
            host=str(host),
            port=int(port),
            database=str(database),
            username=str(username),
        )

    missing = [
        name
        for name, value in (
            ("DATABASE_HOST", settings.database_host),
            ("DATABASE_PORT", settings.database_port),
            ("DATABASE_NAME", settings.database_name),
            ("DATABASE_USER", settings.database_user),
            ("DATABASE_PASSWORD", settings.database_password),
        )
        if value in (None, "")
    ]
    if missing:
        raise RuntimeError(_missing_fields_message(missing))

    resolved_url = str(
        URL.create(
            "postgresql+psycopg",
            username=settings.database_user,
            password=settings.database_password,
            host=settings.database_host,
            port=int(settings.database_port),
            database=settings.database_name,
            query={"sslmode": settings.database_sslmode},
        )
    )
    return ResolvedDatabaseConfig(
        url=resolved_url,
        host=str(settings.database_host),
        port=int(settings.database_port),
        database=str(settings.database_name),
        username=str(settings.database_user),
    )


DATABASE_CONFIG = _resolve_database_config()

engine: AsyncEngine = create_async_engine(
    DATABASE_CONFIG.url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
    pool_timeout=30,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def test_connection() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def initialize_database() -> None:
    logger.info(
        "Database configuration | host=%s port=%s database=%s user=%s",
        DATABASE_CONFIG.host,
        DATABASE_CONFIG.port,
        DATABASE_CONFIG.database,
        DATABASE_CONFIG.username,
    )
    await test_connection()
    logger.info("Database connection test succeeded")
