import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from auth.service import AuthService
from auth.schemas import ChangePasswordSchema
from tests.factories import UserFactory


@pytest.mark.asyncio
async def test_change_password_old_password_incorrect():
    """
    Tests that attempting to change a user's password with an incorrect old password raises
    an HTTPException with a status code of 400 and a detail message indicating
    that the old password is incorrect.
    """
    user = UserFactory.build()
    user.verify_password = MagicMock(return_value=False)

    mock_repo = AsyncMock()
    service = AuthService(mock_repo, MagicMock(), MagicMock())

    data = ChangePasswordSchema(
        old_password="WrongPass1!",
        new_password="Newpass123!"
    )

    with pytest.raises(HTTPException) as exc:
        await service.change_password(user, data)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Old password is incorrect."


@pytest.mark.asyncio
async def test_change_password_db_error():
    """
    Tests that attempting to change the password for a user raises an HTTPException
    with a status code of 500 when a DB error occurs.

    Ensures that the rollback method is called once on the repo.
    """
    user = UserFactory.build()
    user.verify_password = MagicMock(return_value=True)

    mock_repo = AsyncMock()
    mock_repo.commit = AsyncMock(side_effect=SQLAlchemyError("DB error"))
    mock_repo.rollback = AsyncMock()

    service = AuthService(mock_repo, MagicMock(), MagicMock())

    data = ChangePasswordSchema(
        old_password="Password123!",
        new_password="Newpass123!"
    )

    with pytest.raises(HTTPException) as exc:
        await service.change_password(user, data)

    assert exc.value.status_code == 500
    mock_repo.rollback.assert_called_once()


# =====================================
# Happy path → commit + success message
# =====================================
@pytest.mark.asyncio
async def test_change_password_success():
    """
    Tests that attempting to change the password for a user with a valid old password
    and a valid new password returns a response with a success message.

    Ensures that the commit method is called once on the repo, and the response message
    is "Password changed successfully."
    """
    user = UserFactory.build()
    user.verify_password = MagicMock(return_value=True)

    mock_repo = AsyncMock()
    mock_repo.commit = AsyncMock()

    service = AuthService(mock_repo, MagicMock(), MagicMock())

    data = ChangePasswordSchema(
        old_password="Password123!",
        new_password="Newpass123!"
    )

    response = await service.change_password(user, data)

    mock_repo.commit.assert_called_once()
    assert response.message == "Password changed successfully."
