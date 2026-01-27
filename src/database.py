# src/database.py
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine

from config import get_settings


settings = get_settings()


class Base(DeclarativeBase):
    @classmethod
    def default_order_by(cls):
        return None


# --- Async Postgres engine & session (main app) ---

POSTGRESQL_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
    f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
    f"{settings.POSTGRES_DB_PORT}/{settings.POSTGRES_DB}"
)

async_engine = create_async_engine(POSTGRESQL_DATABASE_URL, echo=True)

AsyncSessionLocal = async_sessionmaker(  # type: ignore
    bind=async_engine,
    class_=AsyncSession,  # class to use to create new Session (an alternate class to .orm.session.Session)
    autocommit=False,  # you must explicitly persist changes, otherwise changes are rolled back when session is closed
    autoflush=False,  # pending changes stay in memory until you explicitly call session.flush() or session.commit()
    expire_on_commit=False,  # objects remain in memory with their current values after commit
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    An async generator yielding an AsyncSession instance for the main app.

    This function provides an async generator yielding an AsyncSession instance.
    It ensures that the session is properly initialized and closed after use.

    :return: An async generator yielding an AsyncSession instance.
    :rtype: AsyncGenerator[AsyncSession, None]
    """
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def get_db_contextmanager() -> AsyncGenerator[AsyncSession, None]:
    """
    An async context manager for PostgreSQL database sessions.

    This function provides an async context manager yielding an AsyncSession instance.
    It ensures that the session is properly initialized and closed after use.

    :return: An async generator yielding an AsyncSession instance.
    :rtype: AsyncGenerator[AsyncSession, None]
    """
    async with AsyncSessionLocal() as session:
        yield session


# --- Sync engine for Alembic migrations ---

sync_database_url = POSTGRESQL_DATABASE_URL.replace(
    "postgresql+asyncpg", "postgresql"
)
sync_engine = create_engine(sync_database_url, echo=False)
