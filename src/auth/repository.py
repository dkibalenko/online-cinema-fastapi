from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from auth.models import (
    TokenBaseModel,
    User,
    UserGroup,
    ActivationToken,
    PasswordResetToken,
    RefreshToken,
    UserGroupEnum
)


class UserRepository:
    """
    Repository for user-related database operations.
    """
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

    def add(self, obj: Any) -> None:
        self.db.add(obj)

    async def flush(self) -> None:
        await self.db.flush()

    async def commit(self) -> None:
        await self.db.commit()

    async def refresh(self, obj: Any) -> None:
        await self.db.refresh(obj)

    async def rollback(self) -> None:
        await self.db.rollback()

    async def delete_activation_token(self, token: ActivationToken) -> None:
        await self.db.delete(token)

    async def get_activation_token_record(
        self,
        email: str,
        token: str
    ) -> ActivationToken | None:
        """
        Retrieves the activation token record with the given email and token.

        Args:
            email (str): The email address associated with the activation token.
            token (str): The activation token.

        Returns:
            ActivationToken | None: The activation token record if found, otherwise None.
        """
        stmt = (
            select(ActivationToken)
            .options(joinedload(ActivationToken.user))  # eager loading
            .join(User)  # for filtering. Effects WHERE clause
            .where(
                User.email == email,
                ActivationToken.token == token
            )
        )

        result = await self.db.execute(stmt)
        # After joinedload() use .unique() that deduplicates ORM objects
        return result.unique().scalar_one_or_none()

    # later: methods for tokens, activation, refresh, etc.
