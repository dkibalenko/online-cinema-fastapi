import pytest
from fastapi.exceptions import HTTPException

from users.enums import UserGroupEnum
from auth.dependencies import require_role


def test_require_role_allowed():
    """
    Tests that the require_role dependency returns the current user if the user has the required role.

    Ensures that the require_role method returns the current user if the user has the required role.

    Parameters:
        None

    Returns:
        None
    """
    class FakeUser:
        def has_group(self, group):
            return group == UserGroupEnum.ADMIN

    dep = require_role(UserGroupEnum.ADMIN)
    result = dep(FakeUser())

    assert result is not None


def test_require_role_forbidden():
    """
    Tests that the require_role dependency raises an HTTPException with a status code of 403
    when the current user does not have the required role.

    Ensures that the require_role method raises an HTTPException with a status code of 403
    when the user does not have the required role.

    Parameters:
        None

    Returns:
        None
    """
    class FakeUser:
        def has_group(self, group):
            return False

    dep = require_role(UserGroupEnum.ADMIN)

    with pytest.raises(HTTPException) as exc:
        dep(FakeUser())

    assert exc.value.status_code == 403
    assert "required role(s): admin" in exc.value.detail.lower()
