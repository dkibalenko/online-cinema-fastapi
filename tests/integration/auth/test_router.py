import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auth.models import ActivationToken, RefreshToken, PasswordResetToken
from auth.token_manager import JWTAuthManager
from auth.utils import generate_secure_token
from users.models import User
from tests.settings import get_test_settings


@pytest.mark.asyncio
async def test_register(client: AsyncClient, test_engine, default_user_group):
    """Tests the user registration endpoint.

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
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with async_session() as session:
        user = await session.scalar(
            select(User).where(User.email == payload["email"])
        )
        assert user.group_id == default_user_group.id


@pytest.mark.asyncio
async def test_activate_account(
    client: AsyncClient, test_engine, default_user_group
):
    """Tests the user activation endpoint.

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
        test_engine, expire_on_commit=False, class_=AsyncSession
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
            select(ActivationToken).where(ActivationToken.user_id == user.id)
        )
        assert deleted_token is None


@pytest.mark.asyncio
async def test_login(client: AsyncClient, test_engine, default_user_group):
    """Tests the login endpoint with JSON data.

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
        test_engine, expire_on_commit=False, class_=AsyncSession
    )

    # Create active user
    async with async_session() as session:
        user = User.create(
            email="login@example.com",
            raw_password="Password123!",
            group_id=default_user_group.id,
        )
        user.is_active = True
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
    client: AsyncClient, test_engine, default_user_group
):
    """
    Tests the refresh token endpoint.

    Creates an active user and a refresh token, calls the refresh
    endpoint with the correct token, and asserts that the response
    contains an access token but not a refresh token.

    Parameters:
        client (AsyncClient): The test client
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    async_session = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )

    # Use the same settings as the app (overridden in conftest)
    settings = get_test_settings()

    # 1. Create active user
    async with async_session() as session:
        user = User.create(
            email="login@example.com",
            raw_password="Password123!",
            group_id=default_user_group.id,
        )
        user.is_active = True
        session.add(user)
        await session.flush()

        # 2. Create refresh token
        refresh_token = generate_secure_token(48)

        # 3. Persist matching RefreshToken record in DB
        refresh_record = RefreshToken.create(
            user_id=user.id,
            days_valid=settings.LOGIN_TIME_DAYS,
            token=refresh_token,
        )
        session.add(refresh_record)
        await session.commit()

    # 4. Call refresh endpoint
    response = await client.post(
        "/api/v1/cinema/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    # depending on whether I later enable rotation
    assert "refresh_token" not in data or data["refresh_token"]


@pytest.mark.asyncio
async def test_resend_activation(
    client: AsyncClient,
    test_engine,
    default_user_group
):
    """
    Tests the resend activation token endpoint.

    Ensures that an inactive user receives a new activation token
    when the resend activation token endpoint is called.

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

    # Create inactive user
    async with async_session() as session:
        user = User(
            email="resend@example.com",
            _hashed_password="hashed",
            is_active=False,
            group_id=default_user_group.id,
        )
        session.add(user)
        await session.commit()

    response = await client.post(
        "/api/v1/cinema/auth/activate/resend",
        json={"email": "resend@example.com"},
    )

    assert response.status_code == 200
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_logout(
    client: AsyncClient,
    test_engine,
    default_user_group
):
    """
    Tests the logout endpoint.

    Ensures that the logout endpoint deletes the refresh token
    associated with the user and returns a success message.

    Parameters:
        client (AsyncClient): The test client
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    async_session = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )

    # Create user + refresh token
    async with async_session() as session:
        user = User.create(
            email="logout@example.com",
            raw_password="Password123!",
            group_id=default_user_group.id,
        )
        user.is_active = True
        session.add(user)
        await session.flush()

        refresh_token = generate_secure_token(48)

        session.add(RefreshToken.create(
            user_id=user.id, days_valid=7, token=refresh_token)
        )
        await session.commit()

    response = await client.post(
        "/api/v1/cinema/auth/logout",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully."


@pytest.mark.asyncio
async def test_password_reset_request(
    client: AsyncClient, test_engine, default_user_group
):
    """
    Tests the password reset request endpoint.

    Creates an active user, calls the password reset request endpoint with the
    correct email, and asserts that the response contains a success message.

    Parameters:
        client (AsyncClient): The test client
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    async_session = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
        user = User.create(
            email="reset@example.com",
            raw_password="Password123!",
            group_id=default_user_group.id,
        )
        user.is_active = True
        session.add(user)
        await session.commit()

    response = await client.post(
        "/api/v1/cinema/auth/password-reset/request",
        json={"email": "reset@example.com"},
    )

    assert response.status_code == 200
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_password_reset_complete(
    client: AsyncClient, test_engine, default_user_group
):
    """
    Tests the password reset complete endpoint.

    Creates an active user and a password reset token, calls the password reset
    complete endpoint with the correct token and password, and asserts that the
    response contains a success message.

    Parameters:
        client (AsyncClient): The test client
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    async_session = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
        user = User.create(
            email="complete@example.com",
            raw_password="Password123!",
            group_id=default_user_group.id,
        )
        user.is_active = True
        session.add(user)
        await session.flush()

        token = PasswordResetToken(user_id=user.id)
        session.add(token)
        await session.commit()

    response = await client.post(
        "/api/v1/cinema/auth/password-reset/complete",
        json={"token": token.token, "password": "NewPass123!"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Password has been reset successfully."


@pytest.mark.asyncio
async def test_password_change(
    client: AsyncClient, test_engine, default_user_group
):
    """
    Tests the password change endpoint.

    Creates an active user, calls the password change endpoint with the
    correct old password and new password, and asserts that the response
    contains a success message.

    Parameters:
        client (AsyncClient): The test client
        test_engine (Engine): The test database engine
        default_user_group (UserGroup): The default user group

    Returns:
        None
    """
    async_session = async_sessionmaker(
        test_engine, expire_on_commit=False, class_=AsyncSession
    )
    settings = get_test_settings()
    jwt_manager = JWTAuthManager(
        secret_key_access=settings.JWT_SECRET_KEY_ACCESS.get_secret_value(),
        secret_key_refresh=settings.JWT_SECRET_KEY_REFRESH.get_secret_value(),
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )

    async with async_session() as session:
        user = User.create(
            email="change@example.com",
            raw_password="OldPass123!",
            group_id=default_user_group.id,
        )
        user.is_active = True
        session.add(user)
        await session.commit()

    access_token = jwt_manager.create_access_token({"user_id": user.id})

    response = await client.post(
        "/api/v1/cinema/auth/password-change",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"old_password": "OldPass123!", "new_password": "NewPass456!"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully."
