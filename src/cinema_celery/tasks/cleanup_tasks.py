import asyncio
from datetime import datetime, timezone

from sqlalchemy import text

from database import get_db_contextmanager
from cinema_celery.celery_app import app


async def _cleanup_expired_tokens():
    """Delete expired tokens from the database."""

    now = datetime.now(timezone.utc)

    async with get_db_contextmanager() as session:
        await session.execute(
            text("DELETE FROM activation_tokens WHERE expires_at < :now"),
            {"now": now}
        )
        await session.execute(
            text("DELETE FROM password_reset_tokens WHERE expires_at < :now"),
            {"now": now}
        )
        await session.execute(
            text("DELETE FROM refresh_tokens WHERE expires_at < :now"),
            {"now": now}
        )
        await session.commit()


@app.task
def cleanup_expired_tokens():
    loop = asyncio.get_event_loop()

    # If loop is closed (rare), create a new one
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(_cleanup_expired_tokens())
