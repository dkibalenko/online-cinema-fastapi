import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from auth.service import AuthService
from auth.schemas import TokenRefreshRequestSchema
from exceptions import BaseSecurityError
from tests.factories import (
    UserFactory,
    FakeRefreshTokenExpired,
    FakeRefreshToken
)


@pytest.mark.asyncio
async def test_refresh_access_token_invalid_token():
    """
    Tests that attempting to refresh an access token with an invalid refresh token raises
    an HTTPException with a status code of 400.
    """
    mock_repo = AsyncMock()
    mock_jwt = MagicMock()
    mock_email_sender = MagicMock()

    mock_jwt.decode_refresh_token.side_effect = BaseSecurityError("Invalid")

    service = AuthService(mock_repo, mock_jwt, mock_email_sender)

    data = TokenRefreshRequestSchema(refresh_token="badtoken")

    with pytest.raises(HTTPException) as exc:
        await service.refresh_access_token(data)

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_refresh_access_token_not_found():
    """
    Tests that attempting to refresh an access token with an invalid refresh token raises
    an HTTPException with a status code of 401.

    Ensures that the get_refresh_token_record method is called once on the repo, and the
    exception is raised.
    """
    user = UserFactory.build()

    mock_repo = AsyncMock()
    mock_repo.get_refresh_token_record = AsyncMock(return_value=None)

    mock_jwt = MagicMock()
    mock_jwt.decode_refresh_token.return_value = {"user_id": user.id}

    service = AuthService(
        mock_repo, mock_jwt, mock_email_sender := MagicMock()
    )

    data = TokenRefreshRequestSchema(refresh_token="token123")

    with pytest.raises(HTTPException) as exc:
        await service.refresh_access_token(data)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Refresh token not found."


@pytest.mark.asyncio
async def test_refresh_access_token_expired():
    """
    Tests that attempting to refresh an access token with an expired refresh token raises
    an HTTPException with a status code of 401.

    Ensures that the delete_refresh_token method is called once on the repo, and the
    commit method is called once on the repo.
    """
    user = UserFactory.build()

    token_record = FakeRefreshTokenExpired.build()

    mock_repo = AsyncMock()
    mock_repo.get_refresh_token_record = AsyncMock(return_value=token_record)
    mock_repo.delete_refresh_token = AsyncMock()
    mock_repo.commit = AsyncMock()

    mock_jwt = MagicMock()
    mock_jwt.decode_refresh_token.return_value = {"user_id": user.id}

    service = AuthService(
        mock_repo, mock_jwt, mock_email_sender := MagicMock()
    )

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
    Tests that attempting to refresh an access token with a valid refresh token but the user
    does not exist raises an HTTPException with a status code of 404.

    Ensures that the get_refresh_token_record method is called once on the repo, the get_user_by_id
    method is called once on the repo, and the exception is raised.
    """
    user = UserFactory.build()

    token_record = FakeRefreshToken.build()

    mock_repo = AsyncMock()
    mock_repo.get_refresh_token_record = AsyncMock(return_value=token_record)
    mock_repo.get_user_by_id = AsyncMock(return_value=None)

    mock_jwt = MagicMock()
    mock_jwt.decode_refresh_token.return_value = {"user_id": user.id}

    service = AuthService(
        mock_repo, mock_jwt, mock_email_sender := MagicMock()
    )

    data = TokenRefreshRequestSchema(refresh_token="token123")

    with pytest.raises(HTTPException) as exc:
        await service.refresh_access_token(data)

    assert exc.value.status_code == 404
    assert exc.value.detail == "User not found."


@pytest.mark.asyncio
async def test_refresh_access_token_wrong_user():
    """
    Tests that attempting to refresh an access token with a valid refresh token but belonging to
    a different user raises an HTTPException with a status code of 401.

    Ensures that the get_refresh_token_record method is called once on the repo, the get_user_by_id
    method is called once on the repo, and the exception is raised.
    """
    user = UserFactory.build()
    user.id = 1  # Ensure user ID is set for token association
    other_user_id = 999

    token_record = FakeRefreshToken.build(user_id=other_user_id)  # Token belongs to a different user

    mock_repo = AsyncMock()
    mock_repo.get_refresh_token_record = AsyncMock(return_value=token_record)
    mock_repo.get_user_by_id = AsyncMock(return_value=user)

    mock_jwt = MagicMock()
    mock_jwt.decode_refresh_token.return_value = {"user_id": user.id}

    service = AuthService(mock_repo, mock_jwt, mock_email_sender := MagicMock())

    data = TokenRefreshRequestSchema(refresh_token="token123")

    with pytest.raises(HTTPException) as exc:
        await service.refresh_access_token(data)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Refresh token does not belong to this user."


@pytest.mark.asyncio
async def test_refresh_access_token_success():
    """
    Tests that attempting to refresh an access token with a valid refresh token returns a
    response containing the new access token.

    Ensures that the get_refresh_token_record method is called once on the repo, the
    get_user_by_id method is called once on the repo, and the access token is returned
    in the response.
    """
    user = UserFactory.build()
    user.id = 1  # Ensure user ID is set for token association

    token_record = FakeRefreshToken.build()  # Valid token for the user

    mock_repo = AsyncMock()
    mock_repo.get_refresh_token_record = AsyncMock(return_value=token_record)
    mock_repo.get_user_by_id = AsyncMock(return_value=user)

    mock_jwt = MagicMock()
    mock_jwt.decode_refresh_token.return_value = {"user_id": user.id}
    mock_jwt.create_access_token.return_value = "new_access_token"

    service = AuthService(mock_repo, mock_jwt, mock_email_sender := MagicMock())

    data = TokenRefreshRequestSchema(refresh_token="token123")

    response = await service.refresh_access_token(data)

    assert response.access_token == "new_access_token"
    assert response.token_type == "bearer"
