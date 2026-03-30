import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from auth.service import AuthService
from auth.schemas import UserLoginRequestSchema
from tests.factories import UserFactory


@pytest.mark.asyncio
async def test_login_user_not_found():
    """
    Tests that attempting to login a user that does not exist raises an HTTPException
    with a status code of 401.
    """
    mock_repo = AsyncMock()
    mock_repo.get_user_by_email = AsyncMock(return_value=None)

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = UserLoginRequestSchema(
        email="missing@example.com", password="Password123!"
    )
    settings = MagicMock()

    with pytest.raises(HTTPException) as exc:
        await service.login_user(data, settings)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_login_user_invalid_password():
    """
    Tests that attempting to login a user with an invalid password raises an HTTPException
    with a status code of 401.
    """
    user = UserFactory.build()
    user.verify_password = MagicMock(return_value=False)

    mock_repo = AsyncMock()
    mock_repo.get_user_by_email = AsyncMock(return_value=user)

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = UserLoginRequestSchema(email=user.email, password="Wrongpass1!")
    settings = MagicMock()

    with pytest.raises(HTTPException) as exc:
        await service.login_user(data, settings)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_login_user_inactive():
    """
    Tests that attempting to login an inactive user raises an HTTPException
    with a status code of 403.
    """
    user = UserFactory.build()
    user.is_active = False
    user.verify_password = MagicMock(return_value=True)

    mock_repo = AsyncMock()
    mock_repo.get_user_by_email = AsyncMock(return_value=user)

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = UserLoginRequestSchema(email=user.email, password="Password123!")
    settings = MagicMock()

    with pytest.raises(HTTPException) as exc:
        await service.login_user(data, settings)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_login_user_db_error():
    """
    Tests that attempting to login a user when a DB error occurs raises an HTTPException
    with a status code of 500.

    Ensures that the rollback method is called once on the repo.
    """
    user = UserFactory.build()
    user.verify_password = MagicMock(return_value=True)
    user.is_active = True

    mock_repo = AsyncMock()
    mock_repo.get_user_by_email = AsyncMock(return_value=user)
    mock_repo.add = MagicMock()
    mock_repo.commit = AsyncMock(side_effect=SQLAlchemyError("DB error"))
    mock_repo.rollback = AsyncMock()

    mock_jwt = MagicMock()
    mock_jwt.create_refresh_token.return_value = "refresh123"

    mock_email_sender = MagicMock()

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = UserLoginRequestSchema(email=user.email, password="Password123!")
    settings = MagicMock()
    settings.LOGIN_TIME_DAYS = 7

    with pytest.raises(HTTPException) as exc:
        await service.login_user(data, settings)

    assert exc.value.status_code == 500
    mock_repo.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_login_user_success():
    """
    Tests the happy path of the login endpoint.

    Ensures that when the correct email and password are provided, an access token
    and refresh token are generated and returned, and the commit method is called
    once on the repo.
    """
    user = UserFactory.build()
    user.verify_password = MagicMock(return_value=True)
    user.is_active = True

    mock_repo = AsyncMock()
    mock_repo.get_user_by_email = AsyncMock(return_value=user)
    mock_repo.add = MagicMock()
    mock_repo.commit = AsyncMock()

    mock_jwt = MagicMock()
    mock_jwt.create_access_token.return_value = "access123"

    mock_email_sender = MagicMock()

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = UserLoginRequestSchema(email=user.email, password="Password123!")
    settings = MagicMock()
    settings.LOGIN_TIME_DAYS = 7

    response = await service.login_user(data, settings)

    # access token still mocked
    assert response.access_token == "access123"

    # refresh token is a random opaque string
    assert isinstance(response.refresh_token, str)
    assert len(response.refresh_token) > 0

    # ensure repo interactions done
    mock_repo.add.assert_called_once()
    mock_repo.commit.assert_called_once()
