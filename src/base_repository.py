from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def add(self, instance: Any) -> None:
        self.db.add(instance)

    async def delete(self, instance: Any) -> None:
        await self.db.delete(instance)

    async def flush(self) -> None:
        await self.db.flush()

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()

    async def refresh(self, instance: Any) -> None:
        await self.db.refresh(instance)
