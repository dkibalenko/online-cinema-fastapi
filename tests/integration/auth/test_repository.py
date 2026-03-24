import pytest

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from auth.repository import AuthRepository
from auth.models import ActivationToken
from tests.factories import UserFactory, FakeRefreshToken, FakePasswordResetToken


@pytest.mark.asyncio
async def test_get_user_by_id(test_engine, default_user_group):
    """
    Tests the get_user_by_id method of the AuthRepository class.

    Ensures that the method returns a User instance when given a valid user ID,
    and that the method returns None when given an invalid user ID.

    Parameters:
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

    async with async_session as session:
        repo = AuthRepository(session)

        UserFactory._meta.sqlalchemy_session = session
        user = await UserFactory(group_id=default_user_group.id)
        await session.commit()

        found = await repo.get_user_by_id(user.id)

        assert found is not None
        assert found.id == user.id

        missing = await repo.get_user_by_id(99999)
        assert missing is None


@pytest.mark.asyncio
async def test_refresh_method(test_engine, default_user_group):
    """
    Tests the refresh method of the AuthRepository class.

    Ensures that the method properly refreshes a User instance from the database.

    Parameters:
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

    async with async_session as session:
        repo = AuthRepository(session)

        UserFactory._meta.sqlalchemy_session = session
        user = await UserFactory(group_id=default_user_group.id)
        await session.commit()

        # Direct DB update (bypass ORM identity map)
        await session.execute(
            text("UPDATE users SET email='updated@example.com' WHERE id=:id"),
            {"id": user.id},
        )
        await session.commit()

        # Refresh ORM object
        await repo.refresh(user)

        assert user.email == "updated@example.com"


@pytest.mark.asyncio
async def test_rollback_method(test_engine, default_user_group):
    """
    Tests the rollback method of the AuthRepository class.

    Ensures that the method properly rolls back any uncommitted changes to the database.

    Parameters:
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

    async with async_session as session:
        repo = AuthRepository(session)

        UserFactory._meta.sqlalchemy_session = session
        user = UserFactory.build(group_id=default_user_group.id)

        session.add(user)
        await repo.rollback()

        found = await repo.get_user_by_email(user.email)
        assert found is None


@pytest.mark.asyncio
async def test_get_user_by_email(test_engine, default_user_group):
    """
    Tests the get_user_by_email method of the AuthRepository class.

    Ensures that the method returns a User instance when given a valid email address.

    Parameters:
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

    async with async_session as session:
        repo = AuthRepository(session)

        # setup
        UserFactory._meta.sqlalchemy_session = session
        user = await UserFactory(group_id=default_user_group.id)

        await session.commit()

        # act
        found = await repo.get_user_by_email(user.email)

        # assert
        assert found is not None
        assert found.email == user.email


@pytest.mark.asyncio
async def test_get_default_user_group(test_engine, default_user_group):
    """
    Tests the get_default_user_group method of the AuthRepository class.

    Ensures that the method returns a UserGroup instance with the correct ID.

    Parameters:
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

    async with async_session as session:
        repo = AuthRepository(session)

        group = await repo.get_default_user_group()

        assert group is not None
        assert group.id == default_user_group.id


@pytest.mark.asyncio
async def test_get_activation_token_by_user_id(test_engine, default_user_group):
    async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

    async with async_session as session:
        repo = AuthRepository(session)

        UserFactory._meta.sqlalchemy_session = session
        user = await UserFactory(group_id=default_user_group.id)
        await session.flush()

        token = ActivationToken(user_id=user.id, token="abc123")
        session.add(token)
        await session.commit()

        found = await repo.get_activation_token_by_user_id(user.id)

        assert found is not None
        assert found.token == "abc123"

        missing = await repo.get_activation_token_by_user_id(99999)
        assert missing is None



@pytest.mark.asyncio
async def test_get_activation_token_record(test_engine, default_user_group):
    """
    Tests the get_activation_token_record method of the AuthRepository class.

    Ensures that the method returns an ActivationToken instance when given a valid email address and token.

    Parameters:
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

    async with async_session as session:
        repo = AuthRepository(session)

        # setup
        UserFactory._meta.sqlalchemy_session = session
        user = await UserFactory(group_id=default_user_group.id)

        token = ActivationToken(user_id=user.id, token="abc123")
        session.add(token)
        await session.commit()

        # act
        record = await repo.get_activation_token_record(
            email=user.email,
            token="abc123",
        )

        # assert
        assert record is not None
        assert record.token == "abc123"
        assert record.user.email == user.email


@pytest.mark.asyncio
async def test_refresh_token_queries(test_engine, default_user_group):
    """
    Tests the get_refresh_token_record, delete_refresh_token methods of the AuthRepository class.

    Ensures that the get_refresh_token_record method returns a RefreshToken instance when given a valid token,
    and that the delete_refresh_token method deletes the RefreshToken record from the database.

    Parameters:
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

    async with async_session as session:
        repo = AuthRepository(session)

        # setup
        UserFactory._meta.sqlalchemy_session = session
        user = await UserFactory(group_id=default_user_group.id)

        FakeRefreshToken._meta.sqlalchemy_session = session
        await FakeRefreshToken(user_id=user.id, token="refresh123")

        await session.commit()

        # retrieve
        found = await repo.get_refresh_token_record("refresh123")
        assert found is not None
        assert found.user_id == user.id

        # delete
        await repo.delete_refresh_token(found)
        await repo.commit()

        missing = await repo.get_refresh_token_record("refresh123")
        assert missing is None


@pytest.mark.asyncio
async def test_password_reset_token_queries(test_engine, default_user_group):
    """
    Tests the password reset token queries.

    Ensures that the get_password_reset_token and get_password_reset_token_by_user_id methods
    return a PasswordResetToken instance when given a valid token or user_id,
    and that the delete_password_reset_token method deletes the PasswordResetToken record from the database.

    Parameters:
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

    async with async_session as session:
        repo = AuthRepository(session)

        UserFactory._meta.sqlalchemy_session = session
        user = await UserFactory(group_id=default_user_group.id)

        FakePasswordResetToken._meta.sqlalchemy_session = session
        await FakePasswordResetToken(user_id=user.id, token="reset123")

        await session.commit()

        # retrieve by token
        found = await repo.get_password_reset_token("reset123")
        assert found is not None
        assert found.user_id == user.id

        # retrieve by user_id
        found2 = await repo.get_password_reset_token_by_user_id(user.id)
        assert found2 is not None
        assert found2.token == "reset123"

        # delete
        await repo.delete_password_reset_token(found)
        await repo.commit()

        missing = await repo.get_password_reset_token("reset123")
        assert missing is None
