import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from auth.service import AuthService
from auth.schemas import TokenRefreshRequestSchema
from tests.factories import (
    UserFactory,
    FakeRefreshTokenExpired,
    FakeRefreshToken
)


@pytest.mark.asyncio
async def test_refresh_access_token_invalid_token():
    """
    Invalid refresh token → 401 (not found).
    """
    mock_repo = AsyncMock()
    mock_repo.get_refresh_token_record = AsyncMock(return_value=None)

    service = AuthService(mock_repo, MagicMock(), MagicMock())
    data = TokenRefreshRequestSchema(refresh_token="badtoken")

    with pytest.raises(HTTPException) as exc:
        await service.refresh_access_token(data)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Refresh token not found."


@pytest.mark.asyncio
async def test_refresh_access_token_not_found():
    """
    Tests that attempting to refresh the access token with a valid refresh token but the
    refresh token record does not exist in the DB raises an HTTPException with a status
    code of 401 and a detail message indicating that the refresh token is not found.

    Ensures that the get_refresh_token_record method is called once on the repo with the
    valid token, and the exception is raised.
    """
    mock_repo = AsyncMock()
    mock_repo.get_refresh_token_record = AsyncMock(return_value=None)

    service = AuthService(mock_repo, MagicMock(), MagicMock())
    data = TokenRefreshRequestSchema(refresh_token="token123")

    with pytest.raises(HTTPException) as exc:
        await service.refresh_access_token(data)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Refresh token not found."


@pytest.mark.asyncio
async def test_refresh_access_token_expired():
    """
    Expired refresh token → 401 (expired).
    """
    token_record = FakeRefreshTokenExpired.build()

    mock_repo = AsyncMock()
    mock_repo.get_refresh_token_record = AsyncMock(return_value=token_record)
    mock_repo.delete_refresh_token = AsyncMock()
    mock_repo.commit = AsyncMock()

    service = AuthService(mock_repo, MagicMock(), MagicMock())
    data = TokenRefreshRequestSchema(refresh_token="token123")

    with pytest.raises(HTTPException) as exc:
        await service.refresh_access_token(data)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Refresh token expired."
    mock_repo.delete_refresh_token.assert_called_once_with(token_record)
    mock_repo.commit.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_access_token_user_not_found():
    """
    Tests that attempting to refresh the access token with a valid refresh token but the user does not exist
    raises an HTTPException with a status code of 404.

    Ensures that the get_refresh_token_record method is called once on the repo,
    the get_user_by_id method is called once on the repo, and the exception is raised.
    """
    token_record = FakeRefreshToken.build()

    mock_repo = AsyncMock()
    mock_repo.get_refresh_token_record = AsyncMock(return_value=token_record)
    mock_repo.get_user_by_id = AsyncMock(return_value=None)

    service = AuthService(mock_repo, MagicMock(), MagicMock())
    data = TokenRefreshRequestSchema(refresh_token="token123")

    with pytest.raises(HTTPException) as exc:
        await service.refresh_access_token(data)

    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found."


@pytest.mark.asyncio
async def test_refresh_access_token_success():
    """
    Tests that attempting to refresh the access token with a valid refresh token
    returns a new access token.

    Ensures that the get_refresh_token_record method is called once on the repo,
    the get_user_by_id method is called once on the repo, and the
    create_access_token method is called once on the jwt manager.
    """
    user = UserFactory.build()
    user.id = 1

    token_record = FakeRefreshToken.build(user_id=1)

    mock_repo = AsyncMock()
    mock_repo.get_refresh_token_record = AsyncMock(return_value=token_record)
    mock_repo.get_user_by_id = AsyncMock(return_value=user)

    mock_jwt = MagicMock()
    mock_jwt.create_access_token.return_value = "new_access_token"

    service = AuthService(mock_repo, mock_jwt, MagicMock())
    data = TokenRefreshRequestSchema(refresh_token="token123")

    response = await service.refresh_access_token(data)

    assert response.access_token == "new_access_token"
    assert response.token_type == "bearer"
