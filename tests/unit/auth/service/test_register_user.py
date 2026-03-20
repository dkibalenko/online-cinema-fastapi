import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from auth.service import AuthService
from auth.schemas import UserRegistrationRequestSchema
from users.models import User


@pytest.mark.asyncio
async def test_register_user_success(monkeypatch):
    """
    Tests the happy path of the user registration endpoint.

    Ensures that when the correct email and password are provided, a new user
    account is created, an activation token is generated, an email is sent
    confirming the account registration, and the commit method is called once
    on the repo.
    """
    # setup
    mock_repo = AsyncMock()
    mock_repo.get_user_by_email.return_value = None
    mock_repo.get_default_user_group.return_value = MagicMock(id=1)

    mock_repo.add = MagicMock()
    mock_repo.flush = AsyncMock()
    mock_repo.commit = AsyncMock()

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    # mock Celery task
    fake_delay = MagicMock()
    monkeypatch.setattr("auth.service.send_activation_email.delay", fake_delay)

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = UserRegistrationRequestSchema(
        email="test@example.com",
        password="StrongPass123!"
    )

    # act
    user = await service.register_user(data)

    # assert
    assert isinstance(user, User)
    assert mock_repo.add.call_count == 2  # user + token
    mock_repo.commit.assert_called_once()
    fake_delay.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_email_exists(monkeypatch):
    """
    Tests that attempting to register a new user when the email already exists raises
    an HTTPException with a status code of 409.

    Ensures that the add method is not called on the repo, the commit method
    is not called once on the repo, and the fake delay is not called.
    """
    # setup
    mock_repo = AsyncMock()
    mock_repo.get_user_by_email.return_value = MagicMock()  # existing user

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    fake_delay = MagicMock()
    monkeypatch.setattr("auth.service.send_activation_email.delay", fake_delay)

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = UserRegistrationRequestSchema(
        email="exists@example.com",
        password="StrongPass123!"
    )

    # act + assert
    with pytest.raises(HTTPException) as exc:
        await service.register_user(data)

    assert exc.value.status_code == 409
    mock_repo.add.assert_not_called()
    mock_repo.commit.assert_not_called()
    fake_delay.assert_not_called()


@pytest.mark.asyncio
async def test_register_user_default_group_missing(monkeypatch):
    """
    Tests that attempting to register a new user when the default user group is missing raises
    an HTTPException with a status code of 500.

    Ensures that the add method is not called on the repo, the commit method is not called
    once on the repo, and the fake delay is not called.
    """
    # setup
    mock_repo = AsyncMock()
    mock_repo.get_user_by_email.return_value = None
    mock_repo.get_default_user_group.return_value = None  # missing group

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    fake_delay = MagicMock()
    monkeypatch.setattr("auth.service.send_activation_email.delay", fake_delay)

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = UserRegistrationRequestSchema(
        email="new@example.com",
        password="StrongPass123!"
    )

    # act + assert
    with pytest.raises(HTTPException) as exc:
        await service.register_user(data)

    assert exc.value.status_code == 500
    mock_repo.add.assert_not_called()
    mock_repo.commit.assert_not_called()
    fake_delay.assert_not_called()


@pytest.mark.asyncio
async def test_register_user_sqlalchemy_error(monkeypatch):
    """
    Tests that attempting to register a new user when the DB is unavailable raises
    an HTTPException with a status code of 500.

    Ensures that the rollback method is called once on the repo and that the fake
    delay is not called.
    """
    # setup
    mock_repo = AsyncMock()
    mock_repo.get_user_by_email.return_value = None
    mock_repo.get_default_user_group.return_value = MagicMock(id=1)

    mock_repo.add = MagicMock()
    mock_repo.flush.side_effect = SQLAlchemyError("DB error")  # simulate failure
    mock_repo.rollback = AsyncMock()

    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    fake_delay = MagicMock()
    monkeypatch.setattr("auth.service.send_activation_email.delay", fake_delay)

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = UserRegistrationRequestSchema(
        email="fail@example.com",
        password="StrongPass123!"
    )

    # act + assert
    with pytest.raises(HTTPException) as exc:
        await service.register_user(data)

    assert exc.value.status_code == 500
    mock_repo.rollback.assert_called_once()
    fake_delay.assert_not_called()
