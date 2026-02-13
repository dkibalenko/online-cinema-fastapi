from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from users.enums import UserGroupEnum
from users.models import User, UserProfile, UserGroup


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_group(self, user_id: int) -> User | None:
        """
        Retrieves a user by their ID including their associated group.

        :param user_id: The ID of the user to retrieve.
        :return: The user with their associated group, or None if no user is found.
        """
        stmt = (
            select(User)
            .options(joinedload(User.group))
            .where(User.id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_profile(self, user_id: int) -> User | None:
        """
        Retrieves a user by their ID including their associated profile.

        :param user_id: The ID of the user to retrieve.
        :return: The user with their associated profile, or None if no user is found.
        """
        stmt = (
            select(User)
            .options(joinedload(User.profile))  # eager loading
            .where(User.id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> User | None:
        """
        Retrieves a user by their email address.
        """
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default_user_group(self) -> UserGroup | None:
        """
        Retrieves the default user group, i.e. the group with name USER.
        """
        stmt = select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def add(self, instance: Any) -> None:
        self.db.add(instance)

    async def flush(self) -> None:
        await self.db.flush()

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()

    async def refresh(self, instance: Any) -> None:
        await self.db.refresh(instance)
