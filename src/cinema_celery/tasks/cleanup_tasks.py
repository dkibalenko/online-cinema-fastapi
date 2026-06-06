import asyncio
from datetime import UTC, datetime

from sqlalchemy import text

from cinema_celery.celery_app import app
from database import get_db_contextmanager


async def _cleanup_expired_tokens():
    """Delete expired tokens from the database."""
    now = datetime.now(UTC)

    async with get_db_contextmanager() as session:
        await session.execute(
            text("DELETE FROM activation_tokens WHERE expires_at < :now"),
            {"now": now},
        )
        await session.execute(
            text("DELETE FROM password_reset_tokens WHERE expires_at < :now"),
            {"now": now},
        )
        await session.execute(
            text("DELETE FROM refresh_tokens WHERE expires_at < :now"),
            {"now": now},
        )
        await session.commit()


@app.task
def cleanup_expired_tokens():
    """Periodically clean up expired tokens from the database.

    This task is scheduled to run at regular intervals. It
    deletes all expired tokens from the database, including
    activation tokens, password reset tokens, and refresh
    tokens.

    This task is designed to be run in the background by a
    scheduler like Celery or APScheduler. It should not be
    called directly.
    """
    asyncio.run(_cleanup_expired_tokens())
