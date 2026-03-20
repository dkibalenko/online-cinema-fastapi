import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from auth.service import AuthService
from auth.schemas import TokenRefreshRequestSchema
from exceptions import BaseSecurityError
from tests.factories import (
    UserFactory,
    FakeRefreshToken
)


@pytest.mark.asyncio
async def test_logout_user_invalid_token():
    """
    Tests that attempting to logout an active user with an invalid refresh token raises
    an HTTPException with a status code of 400.
    """
    mock_repo = AsyncMock()
    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    mock_jwt.decode_refresh_token.side_effect = BaseSecurityError("Invalid")

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = TokenRefreshRequestSchema(refresh_token="badtoken")

    with pytest.raises(HTTPException) as exc:
        await service.logout_user(data)

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_logout_user_token_not_found():
    """
    Tests that attempting to logout a user with a valid refresh token but the token does not exist
    raises an HTTPException with a status code of 401.

    Ensures that the get_refresh_token_record method is called once on the repo, the
    exception is raised.
    """
    user = UserFactory.build()
    user.id = 1

    mock_repo = AsyncMock()
    mock_repo.get_refresh_token_record = AsyncMock(return_value=None)

    mock_jwt = MagicMock()
    mock_jwt.decode_refresh_token.return_value = {"user_id": user.id}

    service = AuthService(mock_repo, mock_jwt, MagicMock())

    data = TokenRefreshRequestSchema(refresh_token="token123")

    with pytest.raises(HTTPException) as exc:
        await service.logout_user(data)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Refresh token not found."


@pytest.mark.asyncio
async def test_logout_user_wrong_user():
    """
    Tests that attempting to logout an active user with a valid refresh token but belonging to
    someone else raises an HTTPException with a status code of 401.
    """
    user = UserFactory.build()
    user.id = 1

    token_record = FakeRefreshToken.build(user_id=999)  # belongs to someone else

    mock_repo = AsyncMock()
    mock_repo.get_refresh_token_record = AsyncMock(return_value=token_record)

    mock_jwt = MagicMock()
    mock_jwt.decode_refresh_token.return_value = {"user_id": user.id}

    service = AuthService(mock_repo, mock_jwt, MagicMock())

    data = TokenRefreshRequestSchema(refresh_token="token123")

    with pytest.raises(HTTPException) as exc:
        await service.logout_user(data)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Refresh token does not belong to this user."


#===============================================
# Happy path → delete + commit + success message
#===============================================
@pytest.mark.asyncio
async def test_logout_user_success():
    """
    Tests that attempting to logout an active user with a valid refresh token returns a
    success message.

    Ensures that the delete_refresh_token method is called once on the repo, the
    commit method is called once on the repo, and the success message is returned.
    """
    user = UserFactory.build()
    user.id = 1

    token_record = FakeRefreshToken.build(user_id=1)

    mock_repo = AsyncMock()
    mock_repo.get_refresh_token_record = AsyncMock(return_value=token_record)
    mock_repo.delete_refresh_token = AsyncMock()
    mock_repo.commit = AsyncMock()

    mock_jwt = MagicMock()
    mock_jwt.decode_refresh_token.return_value = {"user_id": user.id}

    service = AuthService(mock_repo, mock_jwt, MagicMock())

    data = TokenRefreshRequestSchema(refresh_token="token123")

    response = await service.logout_user(data)

    assert response.message == "Logged out successfully."
    mock_repo.delete_refresh_token.assert_called_once_with(token_record)
    mock_repo.commit.assert_called_once()
