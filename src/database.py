# mypy: ignore-errors

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    @classmethod
    def default_order_by(cls):
        """Default ordering for queries."""
        return


# --- Async Postgres engine & session (main app) ---

POSTGRESQL_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:"
    f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
    f"{settings.POSTGRES_DB_PORT}/{settings.POSTGRES_DB}"
)
async_engine = create_async_engine(
    POSTGRESQL_DATABASE_URL, echo=settings.SQL_ECHO
)

AsyncSessionLocal = async_sessionmaker(  # type: ignore
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # async specific
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """An async generator yielding an AsyncSession instance for the main app.

    Commits on successful completion of the request; rolls back and
    re-raises on any exception. Intended for use via FastAPI's Depends().

    :return: An async generator yielding an AsyncSession instance.
    :rtype: AsyncGenerator[AsyncSession, None]
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_contextmanager() -> AsyncGenerator[AsyncSession, None]:
    """An async context manager for PostgreSQL database sessions.

    Commits on successful completion of the `async with` block; rolls back
    and re-raises on any exception. Intended for use outside FastAPI's
    dependency system (Celery tasks, WebSocket auth, seeding scripts).

    :return: An async generator yielding an AsyncSession instance.
    :rtype: AsyncGenerator[AsyncSession, None]
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# --- Sync engine for Alembic migrations ---

sync_database_url = POSTGRESQL_DATABASE_URL.replace(
    "postgresql+asyncpg", "postgresql"
)
sync_engine = create_engine(sync_database_url, echo=False)
