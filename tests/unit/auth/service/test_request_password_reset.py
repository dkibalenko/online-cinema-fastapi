import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from auth.service import AuthService
from auth.schemas import PasswordResetRequestSchema
from tests.factories import UserFactory


@pytest.mark.asyncio
async def test_password_reset_user_not_found():
    """
    Tests that attempting to request a password reset for a user that does not exist returns
    a response with a message indicating that an email has been sent if the user is registered.
    """
    mock_repo = AsyncMock()
    mock_repo.get_user_by_email = AsyncMock(return_value=None)

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = PasswordResetRequestSchema(email="missing@example.com")

    response = await service.request_password_reset(data, MagicMock())

    assert response.message == "If this email is registered, a reset link has been sent."


@pytest.mark.asyncio
async def test_password_reset_user_inactive():
    """
    Tests that attempting to request a password reset for an inactive user returns a response
    with a message indicating that an email has been sent if the user is registered.
    """
    user = UserFactory.build()
    user.id = 1
    user.is_active = False

    mock_repo = AsyncMock()
    mock_repo.get_user_by_email = AsyncMock(return_value=user)

    service = AuthService(mock_repo, MagicMock(), MagicMock())

    data = PasswordResetRequestSchema(email=user.email)

    response = await service.request_password_reset(data, MagicMock())

    assert response.message == "If this email is registered, a reset link has been sent."


@pytest.mark.asyncio
async def test_password_reset_old_token_deleted(monkeypatch):
    """
    Tests that attempting to request a password reset for an active user with an existing
    password reset token deletes the old token and adds a new one.

    Ensures that the delete_password_reset_token method is called once on the repo with the
    old token, the add method is called once on the repo with the new token, and the
    fake delay is called once.
    """
    user = UserFactory.build()
    user.id = 1
    user.is_active = True

    old_token = MagicMock()

    mock_repo = AsyncMock()
    mock_repo.get_user_by_email = AsyncMock(return_value=user)
    mock_repo.get_password_reset_token_by_user_id = AsyncMock(return_value=old_token)
    mock_repo.delete_password_reset_token = AsyncMock()
    mock_repo.add = MagicMock()
    mock_repo.commit = AsyncMock()

    fake_delay = MagicMock()
    monkeypatch.setattr("auth.service.send_password_reset_email.delay", fake_delay)

    service = AuthService(mock_repo, MagicMock(), MagicMock())

    data = PasswordResetRequestSchema(email=user.email)

    response = await service.request_password_reset(data, MagicMock())

    mock_repo.delete_password_reset_token.assert_called_once_with(old_token)
    mock_repo.add.assert_called_once()
    mock_repo.commit.assert_called_once()
    fake_delay.assert_called_once()

    assert response.message == "If this email is registered, a reset link has been sent."


@pytest.mark.asyncio
async def test_password_reset_db_error(monkeypatch):
    """
    Tests that attempting to request a password reset for an active user raises
    an HTTPException with a status code of 500 when the DB is unavailable.

    Ensures that the rollback method is called once on the repo, and the fake delay
    is not called.
    """
    user = UserFactory.build()
    user.id = 1
    user.is_active = True

    mock_repo = AsyncMock()
    mock_repo.get_user_by_email = AsyncMock(return_value=user)
    mock_repo.get_password_reset_token_by_user_id = AsyncMock(return_value=None)
    mock_repo.add = MagicMock()
    mock_repo.commit = AsyncMock(side_effect=SQLAlchemyError("DB error"))
    mock_repo.rollback = AsyncMock()

    fake_delay = MagicMock()
    monkeypatch.setattr(
        "auth.service.send_password_reset_email.delay", fake_delay
    )

    service = AuthService(mock_repo, MagicMock(), MagicMock())

    data = PasswordResetRequestSchema(email=user.email)

    with pytest.raises(HTTPException) as exc:
        await service.request_password_reset(data, MagicMock())

    assert exc.value.status_code == 500
    mock_repo.rollback.assert_called_once()
    fake_delay.assert_not_called()
