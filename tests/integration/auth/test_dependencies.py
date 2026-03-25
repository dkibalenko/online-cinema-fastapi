from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.exceptions import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from auth.dependencies import get_current_user
from tests.factories import UserFactory


@pytest.mark.asyncio
async def test_get_current_user_valid(
    test_engine, default_user_group, jwt_manager, make_access_token
):
    """
    Tests the get_current_user method of the AuthService class.

    Ensures that the method returns a User instance when given a valid access token,
    and that the method returns None when given an invalid access token.

    Parameters:
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group
        jwt_manager (JWTAuthManager): The JWT authentication manager
        make_access_token (Callable): A function that generates an access token
    """
    async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

    async with async_session as session:
        # Create active user
        UserFactory._meta.sqlalchemy_session = session
        user = await UserFactory(
            group_id=default_user_group.id, is_active=True
        )
        await session.commit()

        token = make_access_token(user.id)

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )

        result = await get_current_user(
            credentials=credentials,
            jwt_manager=jwt_manager,
            db=session,
        )

        assert result.id == user.id


@pytest.mark.asyncio
async def test_get_current_user_invalid_user_id_type(
    test_engine, jwt_manager
):
    """
    Tests that attempting to get the current user with an access token containing a non-integer user ID
    raises an HTTPException with a status code of 401.

    Ensures that the get_current_user method returns None when given an invalid access token.

    Parameters:
        test_engine (Engine): The test database engine
        jwt_manager (JWTAuthManager): The JWT authentication manager
    """
    async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

    async with async_session as session:
        # Create a token with a non-integer user_id
        token = jwt_manager.create_access_token({"user_id": "abc"})

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(
                credentials=credentials,
                jwt_manager=jwt_manager,
                db=session,
            )

        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid token"


@pytest.mark.asyncio
async def test_get_current_user_expired_token(
    test_engine, jwt_manager, make_access_token
):
    """
    Tests that attempting to get the current user with an expired access token raises an HTTPException with a status code of 401.

    Ensures that the get_current_user method returns None when given an expired access token.

    Parameters:
        test_engine (Engine): The test database engine
        jwt_manager (JWTAuthManager): The JWT authentication manager
        make_access_token (Callable): A function that generates an access token
    """
    async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

    async with async_session as session:
        token = make_access_token(1, expires_delta=timedelta(seconds=-1))

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials, jwt_manager, session)

        assert exc.value.status_code == 401
        assert exc.value.detail == "Access token has expired"


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(test_engine, jwt_manager):
    """
    Tests that attempting to get the current user with an invalid access token raises an HTTPException with a status code of 401.

    Ensures that the get_current_user method returns None when given an invalid access token.

    Parameters:
        test_engine (Engine): The test database engine
        jwt_manager (JWTAuthManager): The JWT authentication manager
    """
    async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

    async with async_session as session:
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="not-a-real-token",
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials, jwt_manager, session)

        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid access token"


@pytest.mark.asyncio
async def test_get_current_user_missing_user_id(
    test_engine, jwt_manager, make_token_without_user_id
):
    """
    Tests that attempting to get the current user with an access token missing a user ID
    raises an HTTPException with a status code of 401.

    Ensures that the get_current_user method returns None when given an access token without a user ID.

    Parameters:
        test_engine (Engine): The test database engine
        jwt_manager (JWTAuthManager): The JWT authentication manager
        make_token_without_user_id (Callable): A function that generates an access token without a user ID
    """
    async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

    async with async_session as session:
        token = make_token_without_user_id()

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials, jwt_manager, session)

        assert exc.value.status_code == 401
        assert exc.value.detail == "Token payload missing user ID"


@pytest.mark.asyncio
async def test_get_current_user_user_not_found(
    test_engine, jwt_manager, make_access_token
):
    """
    Tests that attempting to get the current user with an access token of a non-existent user
    raises an HTTPException with a status code of 401.

    Ensures that the get_current_user method returns None when given an access token of a non-existent user.

    Parameters:
        test_engine (Engine): The test database engine
        jwt_manager (JWTAuthManager): The JWT authentication manager
        make_access_token (Callable): A function that generates an access token
    """
    async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

    async with async_session as session:
        token = make_access_token(99999)

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials, jwt_manager, session)

        assert exc.value.status_code == 401
        assert exc.value.detail == "User not found"


@pytest.mark.asyncio
async def test_get_current_user_inactive_user(
    test_engine, default_user_group, jwt_manager, make_access_token
):
    """
    Tests that attempting to get the current user with an access token of an inactive user
    raises an HTTPException with a status code of 403.

    Ensures that the get_current_user method returns None when given an access token of an inactive user.

    Parameters:
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group
        jwt_manager (JWTAuthManager): The JWT authentication manager
        make_access_token (Callable): A function that generates an access token
    """
    async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

    async with async_session as session:
        UserFactory._meta.sqlalchemy_session = session
        user = await UserFactory(group_id=default_user_group.id, is_active=False)
        await session.commit()

        token = make_access_token(user.id)

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token,
        )

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials, jwt_manager, session)

        assert exc.value.status_code == 403
        assert exc.value.detail == "User account is not activated"
