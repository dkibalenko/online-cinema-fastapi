from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

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
    class_=AsyncSession,  # class to use to create new Session (an alternate class to .orm.session.Session)
    autocommit=False,  # you must explicitly persist changes, otherwise changes are rolled back when session is closed
    autoflush=False,  # pending changes stay in memory until you explicitly call session.flush() or session.commit()
    expire_on_commit=False  # objects remain in memory with their current values after commit
)
sync_database_url = POSTGRESQL_DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
sync_postgresql_engine = create_engine(sync_database_url, echo=False)


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
