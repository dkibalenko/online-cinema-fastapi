import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, UTC

from fastapi import HTTPException

from auth.service import AuthService
from auth.schemas import UserActivationRequestSchema


@pytest.mark.asyncio
async def test_activate_account_invalid_token(monkeypatch):
    """
    Tests that attempting to activate an account with an invalid token raises an
    HTTPException with a status code of 400.

    Ensures that the send_activation_complete_email delay is not called and that the
    delete_activation_token method is not called on the repo.
    """
    # Arrange
    mock_repo = AsyncMock()
    mock_repo.get_activation_token_record.return_value = None  # token not found

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    fake_delay = MagicMock()
    monkeypatch.setattr(
        "auth.service.send_activation_complete_email.delay",
        fake_delay
    )

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = UserActivationRequestSchema(
        email="user@example.com",
        token="invalidtoken"
    )

    # Act + Assert
    with pytest.raises(HTTPException) as exc:
        await service.activate_account(data, MagicMock())

    assert exc.value.status_code == 400
    fake_delay.assert_not_called()


@pytest.mark.asyncio
async def test_activate_account_expired_token(monkeypatch):
    """
    Tests that attempting to activate an account with an expired token raises an
    HTTPException with a status code of 400.

    Ensures that the delete_activation_token method is called on the repo with the expired
    token, the commit method is called once on the repo, and the fake delay is not called.

    Parameters:
        monkeypatch (pytest.MonkeyPatch): The monkeypatch fixture.

    Returns:
        None
    """
    # Arrange
    expired_token = MagicMock()
    expired_token.expires_at = datetime.now(UTC) - timedelta(hours=1)

    mock_repo = AsyncMock()
    mock_repo.get_activation_token_record.return_value = expired_token

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    fake_delay = MagicMock()
    monkeypatch.setattr(
        "auth.service.send_activation_complete_email.delay",
        fake_delay
    )

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = UserActivationRequestSchema(
        email="expired@example.com",
        token="expiredtoken"
    )

    # Act + Assert
    with pytest.raises(HTTPException) as exc:
        await service.activate_account(data, MagicMock())

    assert exc.value.status_code == 400
    mock_repo.delete_activation_token.assert_called_once_with(expired_token)
    mock_repo.commit.assert_called_once()
    fake_delay.assert_not_called()


@pytest.mark.asyncio
async def test_activate_account_already_active(monkeypatch):
    """
    Tests that attempting to activate an already active user account raises an
    HTTPException with a status code of 400.

    Ensures that the send_activation_complete_email delay is not called and that the
    delete_activation_token method is not called on the repo.
    """
    # Arrange
    user = MagicMock()
    user.is_active = True

    token_record = MagicMock()
    token_record.expires_at = datetime.now(UTC) + timedelta(hours=1)
    token_record.user = user

    mock_repo = AsyncMock()
    mock_repo.get_activation_token_record.return_value = token_record

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    fake_delay = MagicMock()
    monkeypatch.setattr(
        "auth.service.send_activation_complete_email.delay",
        fake_delay
    )

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = UserActivationRequestSchema(
        email="active@example.com",
        token="validtoken"
    )

    # Act + Assert
    with pytest.raises(HTTPException) as exc:
        await service.activate_account(data, MagicMock())

    assert exc.value.status_code == 400
    fake_delay.assert_not_called()
    mock_repo.delete_activation_token.assert_not_called()

#========================================================
# Happy path → activate user + delete token + send email
#========================================================
@pytest.mark.asyncio
async def test_activate_account_success(monkeypatch):
    """
    Tests the happy path of the user activation endpoint.

    Ensures that when the correct email and token are provided, the user
    account is activated, the token is deleted, and an email is sent
    confirming the account activation.

    """
    # Arrange
    user = MagicMock()
    user.is_active = False

    token_record = MagicMock()
    token_record.expires_at = datetime.now(UTC) + timedelta(hours=1)
    token_record.user = user

    mock_repo = AsyncMock()
    mock_repo.get_activation_token_record.return_value = token_record

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    fake_delay = MagicMock()
    monkeypatch.setattr(
        "auth.service.send_activation_complete_email.delay",
        fake_delay
    )

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = UserActivationRequestSchema(
        email="user@example.com",
        token="validtoken"
    )

    # Act
    response = await service.activate_account(data, MagicMock())

    # Assert
    assert response.message == "Account activated successfully."
    assert user.is_active is True

    mock_repo.delete_activation_token.assert_called_once_with(token_record)
    mock_repo.commit.assert_called_once()
    fake_delay.assert_called_once()
