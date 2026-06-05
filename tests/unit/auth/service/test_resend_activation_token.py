import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from auth.service import AuthService
from auth.schemas import ResendActivationRequestSchema


class DummyAsyncContextManager:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_resend_activation_user_not_found(monkeypatch):
    """
    Tests that attempting to resend an activation token for a non-existent user raises
    an HTTPException with a status code of 404.

    Ensures that the send_activation_email delay is not called.
    """
    mock_repo = AsyncMock()
    mock_repo.db = MagicMock()
    mock_repo.db.begin.return_value = DummyAsyncContextManager()
    mock_repo.get_user_by_email.return_value = None  # user missing

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    fake_delay = MagicMock()
    monkeypatch.setattr("auth.service.send_activation_email.delay", fake_delay)

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = ResendActivationRequestSchema(email="missing@example.com")

    with pytest.raises(HTTPException) as exc:
        await service.resend_activation_token(data, MagicMock())

    assert exc.value.status_code == 404
    fake_delay.assert_not_called()


@pytest.mark.asyncio
async def test_resend_activation_user_already_active(monkeypatch):
    """
    Tests that attempting to resend an activation token for an already active user raises
    an HTTPException with a status code of 400.

    Ensures that the send_activation_email delay is not called.
    """
    user = MagicMock()
    user.is_active = True

    mock_repo = AsyncMock()
    mock_repo.db = MagicMock()
    mock_repo.db.begin.return_value = DummyAsyncContextManager()
    mock_repo.get_user_by_email.return_value = user

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    fake_delay = MagicMock()
    monkeypatch.setattr("auth.service.send_activation_email.delay", fake_delay)

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = ResendActivationRequestSchema(email="active@example.com")

    with pytest.raises(HTTPException) as exc:
        await service.resend_activation_token(data, MagicMock())

    assert exc.value.status_code == 400
    fake_delay.assert_not_called()


@pytest.mark.asyncio
async def test_resend_activation_deletes_old_token(monkeypatch):
    """
    Tests that attempting to resend an activation token for an inactive user deletes the
    old token and adds a new one.

    Ensures that the delete_activation_token method is called once on the repo with the
    old token, the add method is called once on the repo with the new token, and the
    fake delay is called once.
    """
    user = MagicMock()
    user.is_active = False
    user.id = 1

    old_token = MagicMock()

    mock_repo = AsyncMock()
    mock_repo.db = MagicMock()
    mock_repo.db.begin.return_value = DummyAsyncContextManager()

    mock_repo.get_user_by_email = AsyncMock(return_value=user)
    mock_repo.get_activation_token_by_user_id = AsyncMock(return_value=old_token)
    mock_repo.delete_activation_token = AsyncMock()
    mock_repo.add = MagicMock()

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    fake_delay = MagicMock()
    monkeypatch.setattr("auth.service.send_activation_email.delay", fake_delay)

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = ResendActivationRequestSchema(email="user@example.com")

    response = await service.resend_activation_token(data, MagicMock())

    assert response.message == "A new activation link has been sent to your email."
    mock_repo.delete_activation_token.assert_called_once_with(old_token)
    mock_repo.add.assert_called_once()  # new token added
    fake_delay.assert_called_once()


#==========================================================
# Happy path (no old token) → create new token + send email
#==========================================================
@pytest.mark.asyncio
async def test_resend_activation_success(monkeypatch):
    """
    Tests that attempting to resend an activation token for an inactive user with no
    existing token creates a new token and sends an email with the new token.

    Ensures that the add method is called once on the repo with the new token, and the
    fake delay is called once.
    """
    user = MagicMock()
    user.is_active = False
    user.id = 1

    mock_repo = AsyncMock()
    mock_repo.db = MagicMock()
    mock_repo.db.begin.return_value = DummyAsyncContextManager()

    mock_repo.get_user_by_email = AsyncMock(return_value=user)
    mock_repo.get_activation_token_by_user_id = AsyncMock(return_value=None)
    mock_repo.add = MagicMock()

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    fake_delay = MagicMock()
    monkeypatch.setattr("auth.service.send_activation_email.delay", fake_delay)

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = ResendActivationRequestSchema(email="user@example.com")

    response = await service.resend_activation_token(data, MagicMock())

    assert response.message == "A new activation link has been sent to your email."
    mock_repo.add.assert_called_once()
    fake_delay.assert_called_once()


@pytest.mark.asyncio
async def test_resend_activation_sqlalchemy_error(monkeypatch):
    """
    Tests that attempting to resend an activation token for an inactive user raises
    an HTTPException with a status code of 500 when the DB is unavailable.

    Ensures that the fake delay is not called.
    """
    mock_repo = AsyncMock()
    mock_repo.db = MagicMock()
    mock_repo.db.begin.return_value = DummyAsyncContextManager()

    mock_repo.get_user_by_email = AsyncMock(
        side_effect=SQLAlchemyError("DB error")
    )

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    fake_delay = MagicMock()
    monkeypatch.setattr("auth.service.send_activation_email.delay", fake_delay)

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = ResendActivationRequestSchema(email="user@example.com")

    with pytest.raises(HTTPException) as exc:
        await service.resend_activation_token(data, MagicMock())

    assert exc.value.status_code == 500
    fake_delay.assert_not_called()
