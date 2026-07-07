<<<<<<< HEAD
from app.core.database import SessionLocal as AsyncSessionFactory, engine, get_db

get_db_session = get_db
=======
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        yield session

>>>>>>> 7eb62467f7ddba40d63bec4ba2a4f0e25bb3a894
