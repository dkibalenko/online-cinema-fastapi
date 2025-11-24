from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import get_settings


settings = get_settings()

POSTGRESQL_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
    f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
    f"{settings.POSTGRES_DB_PORT}/{settings.POSTGRES_DB}"
)

postgresql_engine = create_async_engine(POSTGRESQL_DATABASE_URL, echo=False)

AsyncPostgresqlSessionLocal = sessionmaker(  # type: ingore
    bind=postgresql_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

async def get_postgresql_db() -> AsyncGenerator[AsyncSession, None]:

    """
    An async generator yielding an AsyncSession instance for PostgreSQL database.

    This function returns an async generator yielding an AsyncSession instance.
    It ensures that the session is properly initialized and closed after use.

    :yield: An AsyncSession instance.
    :rtype: AsyncGenerator[AsyncSession, None]
    """
    async with AsyncPostgresqlSessionLocal() as session:
        yield session


@asynccontextmanager
async def get_postgresql_db_contexmanager() -> AsyncGenerator[AsyncSession, None]:
    """
    An async context manager for PostgreSQL database sessions.

    This function provides an async context manager yielding an
    AsyncSession instance. It ensures that the session is
    properly initialized and closed after use.

    :return: An async generator yielding an AsyncSession instance.
    """
    async with AsyncPostgresqlSessionLocal() as session:
        yield session
