from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from auth.models import ActivationToken, PasswordResetToken, RefreshToken
from users.enums import UserGroupEnum
from users.models import User, UserGroup


class AuthRepository:  # rename to AuthRepository
    """Repository for user-related database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: int) -> User | None:
        """Retrieves a user by their ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Retrieves a user by their email address."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default_user_group(self) -> UserGroup | None:
        """Retrieves the default user group, i.e. the group with name USER."""
        stmt = select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def add(self, obj: Any) -> None:
        """Adds an object to the current database session.

        This method adds an object to the current database session, scheduling
        it for insertion into the database when the session is flushed or
        committed.

        :param obj: The object to add to the database session.
        :return: None
        """
        self.db.add(obj)

    async def flush(self) -> None:
        """Flushes the current database session.

        This method flushes the current database session, saving any
        pending changes to the database.

        :return: None
        """
        await self.db.flush()

    async def commit(self) -> None:
        """Commits the current database transaction.

        This method commits the current database transaction, persisting
        any changes made to the database.

        :return: None
        """
        await self.db.commit()

    async def refresh(self, obj: Any) -> None:
        """Refreshes the given object in the current database session.

        This method refreshes the given object in the current database session.
        It can be used to reload the object from the database after changes
        have been made.

        :param obj: The object to refresh.
        :return: None
        """
        await self.db.refresh(obj)

    async def rollback(self) -> None:
        """Rolls back the current database transaction.

        This method rolls back the current database transaction. It can be used
        to revert changes made to the database in case of an error.

        :return: None
        """
        await self.db.rollback()

    async def delete_activation_token(self, token: ActivationToken) -> None:
        """Deletes an activation token from the database.

        Args:
            token (ActivationToken): The activation token to delete.

        Returns:
            None
        """
        await self.db.delete(token)

    async def get_activation_token_record(
        self, email: str, token: str
    ) -> ActivationToken | None:
        """Retrieves the activation token record.

        This method retrieves the activation token record associated
        with the given email and token.
        """
        stmt = (
            select(ActivationToken)
            .options(joinedload(ActivationToken.user))  # eager loading
            .join(User)  # for filtering. Effects WHERE clause
            .where(User.email == email, ActivationToken.token == token)
        )

        result = await self.db.execute(stmt)
        # After joinedload() use .unique() that deduplicates ORM objects
        return result.unique().scalar_one_or_none()

    async def get_activation_token_by_user_id(
        self, user_id: int
    ) -> ActivationToken | None:
        """Retrieves the activation token record.

        This method retrieves the activation token record associated with
        the given user ID.
        """
        stmt = select(ActivationToken).where(
            ActivationToken.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_refresh_token_record(
        self, token: str
    ) -> RefreshToken | None:
        """Retrieves the refresh token record with the given token."""
        stmt = select(RefreshToken).where(RefreshToken.token == token)
        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()

    async def delete_refresh_token(self, token: RefreshToken) -> None:
        """Deletes a refresh token from the database.

        Args:
            token (RefreshToken): The refresh token to delete.

        Returns:
            None
        """
        await self.db.delete(token)

    async def get_password_reset_token(
        self, token: str
    ) -> PasswordResetToken | None:
        """Retrieves the password reset token record.

        This method retrieves the password reset token record associated with
        the given token.
        """
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token == token
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_password_reset_token_by_user_id(
        self, user_id: int
    ) -> PasswordResetToken | None:
        """Retrieves the password reset token record.

        This method retrieves the password reset token record associated with
        the given user ID.
        """
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_password_reset_token(
        self, token: PasswordResetToken
    ) -> None:
        """Deletes a password reset token from the database.

        Args:
            token (PasswordResetToken): The password reset token to delete.

        Returns:
            None
        """
        await self.db.delete(token)
