from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def add(self, instance: Any) -> None:
        """Stage instance for insertion."""
        self.db.add(instance)

    async def delete(self, instance: Any) -> None:
        """Mark instance for deletion."""
        await self.db.delete(instance)

    async def flush(self) -> None:
        """Flush pending changes to the DB without committing."""
        await self.db.flush()

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.db.commit()

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        await self.db.rollback()

    async def refresh(self, instance: Any) -> None:
        """Refresh instance attributes from the DB."""
        await self.db.refresh(instance)
