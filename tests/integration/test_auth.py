import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from tests.settings import get_test_settings
from auth.token_manager import JWTAuthManager
from users.models import User
from auth.models import ActivationToken, RefreshToken


@pytest.mark.asyncio
async def test_register(client: AsyncClient, test_engine, default_user_group):
    """
    Tests the user registration endpoint.

    Ensures that a new user is created with the correct group ID,
    and that the user is inserted into the database correctly.

    Parameters:
        client (AsyncClient): The test client
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    payload = {"email": "testuser@example.com", "password": "StrongPass123!"}
    response = await client.post("/api/v1/cinema/auth/register", json=payload)

    assert response.status_code == 201

    async_session = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )
    async with async_session() as session:
        user = await session.scalar(
            select(User).where(User.email == payload["email"])
        )
        assert user.group_id == default_user_group.id


@pytest.mark.asyncio
async def test_activate_account(
    client: AsyncClient,
    test_engine,
    default_user_group
):
    """
    Tests the user activation endpoint.

    Creates a user and an activation token, calls the activation endpoint
    with the correct email and token, and asserts that the user is activated
    and the token is deleted.

    Parameters:
        client (AsyncClient): The test client
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    async_session = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )

    # Create user + activation token
    async with async_session() as session:
        user = User(
            email="activate_me@example.com",
            _hashed_password="hashed",
            is_active=False,
            group_id=default_user_group.id,
        )
        session.add(user)
        await session.flush()

        token = ActivationToken(user_id=user.id)
        session.add(token)
        await session.commit()
        await session.refresh(user)
        await session.refresh(token)

    # Call the real activation endpoint
    response = await client.post(
        "/api/v1/cinema/auth/activate",
        json={"email": user.email, "token": token.token},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Account activated successfully."

    # Verify user activated + token removed
    async with async_session() as session:
        refreshed_user = await session.get(User, user.id)
        assert refreshed_user.is_active is True

        deleted_token = await session.scalar(
            select(ActivationToken)
            .where(ActivationToken.user_id == user.id)
        )
        assert deleted_token is None


@pytest.mark.asyncio
async def test_login(client: AsyncClient, test_engine, default_user_group):
    """
    Tests the login endpoint with JSON data.

    Creates an active user, calls the login endpoint with the correct
    email and password, and asserts that the response contains an access
    token and a refresh token.

    Parameters:
        client (AsyncClient): The test client
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    async_session = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )

    # Create active user
    async with async_session() as session:
        user = User.create(
            email="login@example.com",
            raw_password="Password123!",
            group_id=default_user_group.id,
        )
        user.is_active=True
        session.add(user)
        await session.commit()
        await session.refresh(user)

    # Call login with JSON (not form data)
    response = await client.post(
        "/api/v1/cinema/auth/login",
        json={"email": user.email, "password": "Password123!"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_token(
    client: AsyncClient,
    test_engine,
    default_user_group
):
    """
    Tests the refresh token endpoint.

    Creates an active user and a refresh token JWT with user_id claim,
    persists the matching RefreshToken record in the database,
    calls the refresh endpoint with the correct refresh token,
    and asserts that the response contains a new access token and
    does not contain a new refresh token (depending on whether rotation is
    enabled).

    Parameters:
        client (AsyncClient): The test client
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    async_session = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )

    # Use the same settings as the app (overridden in conftest)
    settings = get_test_settings()
    jwt_manager = JWTAuthManager(
        secret_key_access=settings.JWT_SECRET_KEY_ACCESS.get_secret_value(),
        secret_key_refresh=settings.JWT_SECRET_KEY_REFRESH.get_secret_value(),
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )

    # 1. Create active user
    async with async_session() as session:
        user = User.create(
            email="login@example.com",
            raw_password="Password123!",
            group_id=default_user_group.id,
        )
        user.is_active=True
        session.add(user)
        await session.flush()

        # 2. Create refresh token JWT with user_id claim
        refresh_jwt = jwt_manager.create_refresh_token({"user_id": user.id})

        # 3. Persist matching RefreshToken record in DB
        refresh_record = RefreshToken.create(
            user_id=user.id,
            days_valid=settings.LOGIN_TIME_DAYS,
            token=refresh_jwt,
        )
        session.add(refresh_record)
        await session.commit()

    # 4. Call refresh endpoint
    response = await client.post(
        "/api/v1/cinema/auth/refresh",
        json={"refresh_token": refresh_jwt},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    # depending on whether I later enable rotation
    assert "refresh_token" not in data or data["refresh_token"]
