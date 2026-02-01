from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from auth.models import (
    User,
    UserGroup,
    ActivationToken,
    PasswordResetToken,
    RefreshToken,
    UserGroupEnum
)


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        """
        Retrieves a user by their email address.

        Args:
            email (str): The user's email address.

        Returns:
            User | None: The user object if found, otherwise None.
        """
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default_user_group(self) -> UserGroup | None:
        """
        Retrieves the default user group, i.e. the group with name USER.

        Returns:
            UserGroup | None: The default user group if found, otherwise None.
        """
        stmt = select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def add(self, user: User) -> None:
        self.db.add(user)

    async def flush(self) -> None:
        await self.db.flush()

    async def commit(self) -> None:
        await self.db.commit()

    async def refresh(self, user: User) -> None:
        await self.db.refresh(user)

    async def rollback(self) -> None:
        await self.db.rollback()

    # later: methods for tokens, activation, refresh, etc.
