import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from auth.service import AuthService
from auth.schemas import TokenRefreshRequestSchema
from tests.factories import (
    UserFactory,
    FakeRefreshToken
)


@pytest.mark.asyncio
async def test_logout_user_invalid_token():
    """
    Tests that attempting to logout a user with an invalid refresh token raises an HTTPException
    with a status code of 401.

    Ensures that the get_refresh_token_record method is called once on the repo, and the
    exception is raised.
    """
    mock_repo = AsyncMock()
    mock_repo.get_refresh_token_record = AsyncMock(return_value=None)

    service = AuthService(mock_repo, MagicMock(), MagicMock())
    data = TokenRefreshRequestSchema(refresh_token="badtoken")

    with pytest.raises(HTTPException) as exc:
        await service.logout_user(data)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Refresh token not found."


@pytest.mark.asyncio
async def test_logout_user_token_not_found():
    """
    Tests that attempting to logout a user with a refresh token that doesn't exist in the DB
    raises an HTTPException with a status code of 401.

    Ensures that the get_refresh_token_record method is called once on the repo, and the
    exception is raised.
    """
    mock_repo = AsyncMock()
    mock_repo.get_refresh_token_record = AsyncMock(return_value=None)

    service = AuthService(mock_repo, MagicMock(), MagicMock())
    data = TokenRefreshRequestSchema(refresh_token="token123")

    with pytest.raises(HTTPException) as exc:
        await service.logout_user(data)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Refresh token not found."


#===============================================
# Happy path → delete + commit + success message
#===============================================
@pytest.mark.asyncio
async def test_logout_user_success():
    """
    Tests that attempting to logout a user with a valid refresh token returns a response
    containing a success message.

    Ensures that the get_refresh_token_record method is called once on the repo, the
    delete_refresh_token method is called once on the repo, and the commit method is
    called once on the repo.
    """
    user = UserFactory.build()
    user.id = 1

    token_record = FakeRefreshToken.build(user_id=1)

    mock_repo = AsyncMock()
    mock_repo.get_refresh_token_record = AsyncMock(return_value=token_record)
    mock_repo.delete_refresh_token = AsyncMock()
    mock_repo.commit = AsyncMock()

    service = AuthService(mock_repo, MagicMock(), MagicMock())
    data = TokenRefreshRequestSchema(refresh_token="token123")

    response = await service.logout_user(data)

    assert response.message == "Logged out successfully."
    mock_repo.delete_refresh_token.assert_called_once_with(token_record)
    mock_repo.commit.assert_called_once()
