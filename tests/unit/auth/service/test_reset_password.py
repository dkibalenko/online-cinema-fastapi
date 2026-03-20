import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from auth.service import AuthService
from auth.schemas import PasswordResetCompleteRequestSchema
from tests.factories import (
    UserFactory,
    FakePasswordResetToken,
    FakePasswordResetTokenExpired
)


@pytest.mark.asyncio
async def test_reset_password_token_not_found():
    """
    Tests that attempting to reset a password with an invalid or expired reset token
    raises an HTTPException with a status code of 400 and a detail message
    indicating that the reset token is invalid or expired.

    Ensures that the get_password_reset_token method is called once on the repo with
    the invalid token, and the exception is raised.
    """
    mock_repo = AsyncMock()
    mock_repo.get_password_reset_token = AsyncMock(return_value=None)

    service = AuthService(mock_repo, MagicMock(), MagicMock())

    data = PasswordResetCompleteRequestSchema(
        token="badtoken",
        password="Password123!"
    )

    with pytest.raises(HTTPException) as exc:
        await service.reset_password(data)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid or expired reset token."


@pytest.mark.asyncio
async def test_reset_password_token_expired():
    """
    Tests that attempting to reset a password with an expired reset token raises an
    HTTPException with a status code of 400 and a detail message indicating that the
    reset token has expired.

    Ensures that the delete_password_reset_token method is called once on the repo with the
    expired token, and the commit method is called once on the repo.
    """
    user = UserFactory.build()
    user.id = 1

    token_record = FakePasswordResetTokenExpired.build()

    mock_repo = AsyncMock()
    mock_repo.get_password_reset_token = AsyncMock(return_value=token_record)
    mock_repo.delete_password_reset_token = AsyncMock()
    mock_repo.commit = AsyncMock()

    service = AuthService(mock_repo, MagicMock(), MagicMock())

    data = PasswordResetCompleteRequestSchema(
        token="expiredtoken",
        password="Password123!"
    )

    with pytest.raises(HTTPException) as exc:
        await service.reset_password(data)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Reset token expired."

    mock_repo.delete_password_reset_token.assert_called_once_with(token_record)
    mock_repo.commit.assert_called_once()


@pytest.mark.asyncio
async def test_reset_password_user_not_found():
    """
    Tests that attempting to reset a password with a valid reset token but the user does not exist
    raises an HTTPException with a status code of 404.

    Ensures that the get_password_reset_token method is called once on the repo, the get_user_by_id
    method is called once on the repo, and the exception is raised.
    """
    token_record = FakePasswordResetToken.build()

    mock_repo = AsyncMock()
    mock_repo.get_password_reset_token = AsyncMock(return_value=token_record)
    mock_repo.get_user_by_id = AsyncMock(return_value=None)

    service = AuthService(mock_repo, MagicMock(), MagicMock())

    data = PasswordResetCompleteRequestSchema(
        token="validtoken",
        password="Password123!"
    )

    with pytest.raises(HTTPException) as exc:
        await service.reset_password(data)

    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found."


@pytest.mark.asyncio
async def test_reset_password_db_error(monkeypatch):
    """
    Tests that attempting to reset a password raises an HTTPException with a status code of 500
    when the DB is unavailable.

    Ensures that the rollback method is called once on the repo, and the fake delay
    is not called.
    """
    user = UserFactory.build()

    token_record = FakePasswordResetToken.build(user_id=user.id)

    mock_repo = AsyncMock()
    mock_repo.get_password_reset_token = AsyncMock(return_value=token_record)
    mock_repo.get_user_by_id = AsyncMock(return_value=user)
    mock_repo.delete_password_reset_token = AsyncMock()
    mock_repo.commit = AsyncMock(side_effect=SQLAlchemyError("DB error"))
    mock_repo.rollback = AsyncMock()

    fake_delay = MagicMock()
    monkeypatch.setattr(
        "auth.service.send_password_reset_complete_email.delay",
        fake_delay
    )

    service = AuthService(mock_repo, MagicMock(), MagicMock())

    data = PasswordResetCompleteRequestSchema(
        token="validtoken",
        password="Password123!"
    )

    with pytest.raises(HTTPException) as exc:
        await service.reset_password(data)

    assert exc.value.status_code == 500
    mock_repo.rollback.assert_called_once()
    fake_delay.assert_not_called()


#==================================================================
# Happy path → update password + delete token + commit + email sent
#==================================================================
@pytest.mark.asyncio
async def test_reset_password_success(monkeypatch):
    """
    Tests the happy path of the password reset endpoint.

    Ensures that when the correct token and password are provided, the user
    password is updated, the token is deleted, and an email is sent
    confirming the password reset.

    """
    user = UserFactory.build()

    token_record = FakePasswordResetToken.build(user_id=user.id)

    mock_repo = AsyncMock()
    mock_repo.get_password_reset_token = AsyncMock(return_value=token_record)
    mock_repo.get_user_by_id = AsyncMock(return_value=user)
    mock_repo.delete_password_reset_token = AsyncMock()
    mock_repo.commit = AsyncMock()

    fake_delay = MagicMock()
    monkeypatch.setattr(
        "auth.service.send_password_reset_complete_email.delay",
        fake_delay
    )

    service = AuthService(mock_repo, MagicMock(), MagicMock())

    data = PasswordResetCompleteRequestSchema(
        token="validtoken",
        password="Password123!"
    )

    response = await service.reset_password(data)

    mock_repo.delete_password_reset_token.assert_called_once_with(token_record)
    mock_repo.commit.assert_called_once()
    fake_delay.assert_called_once_with(
        user.email, "http://127.0.0.1:8000/api/v1/cinema/auth/login"
    )

    assert response.message == "Password has been reset successfully."
