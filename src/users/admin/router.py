from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi_pagination import Page, paginate

from auth.dependencies import require_role
from users.admin.dependencies import (
    get_admin_user_profile_service,
    get_admin_user_service,
)
from users.admin.schemas import (
    AdminResetPasswordSchema,
    AdminUserProfileCreateSchema,
    AdminUserProfileResponse,
    AdminUserProfileUpdateSchema,
    UpdateGroupSchema,
    UserAdminResponse,
    UserFilterParams,
)
from users.admin.services.profile_service import AdminUserProfileService
from users.admin.services.user_service import AdminUserService
from users.models import UserGroupEnum

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role(UserGroupEnum.ADMIN))],
)


@router.get(
    "/users",
    response_model=Page[UserAdminResponse],
    summary="List users with optional filters",
    description=(
        "Lists users with optional filters for email, group, "
        "and active status. Requires admin privileges."
    ),
    responses={
        200: {"description": "A list of users was successfully retrieved."},
        403: {
            "description": (
                "Forbidden. The user does not have admin privileges."
            )
        },
    },
    status_code=status.HTTP_200_OK,
)
async def list_users(
    filters: Annotated[UserFilterParams, Depends()],
    service: Annotated[AdminUserService, Depends(get_admin_user_service)],
) -> Page[UserAdminResponse]:
    """Lists users with optional filters for email, group, and active status.

    Requires admin privileges.

    Parameters:
        filters (UserFilterParams): The filter options.

    Returns:
        Page[UserAdminResponse]: A paginated list of users that match the given
            filters.

    Raises:
        HTTPException: If the user does not have admin privileges.
    """
    users = await service.list_filtered_users(filters)
    return paginate(users)


@router.patch(
    "/users/{user_id}/group",
    response_model=UserAdminResponse,
    summary="Update a user's group",
    description=("Updates the group of a user. Requires admin privileges."),
    responses={
        200: {"description": "The user's group was successfully updated."},
        404: {
            "description": (
                "Not found. The user or the specified group does not exist."
            )
        },
        403: {
            "description": (
                "Forbidden. The user does not have admin privileges."
            )
        },
    },
    status_code=status.HTTP_200_OK,
)
async def update_user_group(
    user_id: int,
    payload: UpdateGroupSchema,
    service: Annotated[AdminUserService, Depends(get_admin_user_service)],
):
    """Updates the group of a user.

    Args:
        user_id (int): The ID of the user to update.
        payload (UpdateGroupSchema): A schema containing the new group for
            the user.
        service (AdminUserService): The admin user service.

    Returns:
        UserAdminResponse: The updated user.

    Raises:
        HTTPException: If the user is not found, if the user does not have
            admin privileges, or if the specified group does not exist.
    """
    return await service.update_group(user_id, payload.group)


@router.post(
    "/users/{user_id}/activate",
    response_model=UserAdminResponse,
    summary="Activate a user account",
    description=(
        "Activates a user account, i.e. sets their is_active flag to True. "
        "Requires admin privileges."
    ),
    responses={
        200: {"description": "The user account was successfully activated."},
        404: {"description": "Not found. The user does not exist."},
        403: {
            "description": (
                "Forbidden. The user does not have admin privileges."
            )
        },
    },
)
async def activate_user(
    user_id: int,
    service: Annotated[AdminUserService, Depends(get_admin_user_service)],
):
    """Activates a user account, i.e. sets their is_active flag to True.

    Args:
        user_id (int): The ID of the user to activate.
        service (AdminUserService): The admin user service.

    Returns:
        UserAdminResponse: The activated user.

    Raises:
        HTTPException: If the user is not found or if the user does not have
            admin privileges.
    """
    return await service.activate_user(user_id)


@router.post(
    "/users/{user_id}/deactivate",
    response_model=UserAdminResponse,
    summary="Deactivate a user account",
    description=(
        "Deactivates a user account, i.e. sets their is_active flag to False. "
        "Requires admin privileges."
    ),
    responses={
        200: {"description": "The user account was successfully deactivated."},
        404: {"description": "Not found. The user does not exist."},
        403: {
            "description": (
                "Forbidden. The user does not have admin privileges."
            )
        },
    },
)
async def deactivate_user(
    user_id: int,
    service: Annotated[AdminUserService, Depends(get_admin_user_service)],
):
    """Deactivates a user account, i.e. sets their is_active flag to False.

    :param user_id: The ID of the user to deactivate.
    :return: The deactivated user.
    :raises HTTPException: If the user is not found or if the user does not
        have admin privileges.
    """
    return await service.deactivate_user(user_id)


@router.post(
    "/users/{user_id}/reset-password",
    response_model=UserAdminResponse,
    summary="Reset a user's password",
    description=("Resets a user's password. Requires admin privileges."),
    responses={
        200: {"description": "The user's password was successfully reset."},
        404: {"description": "Not found. The user does not exist."},
        403: {
            "description": (
                "Forbidden. The user does not have admin privileges."
            )
        },
    },
)
async def reset_password(
    user_id: int,
    payload: AdminResetPasswordSchema,
    service: Annotated[AdminUserService, Depends(get_admin_user_service)],
):
    """Resets a user's password.

    Args:
        user_id (int): The ID of the user to reset the password for.
        payload (AdminResetPasswordSchema): The new password for the user.
        service (AdminUserService): The admin user service.

    Returns:
        UserAdminResponse: The updated user.

    Raises:
        HTTPException: If the user does not exist or if the user does not have
        admin privileges.
    """
    return await service.reset_password(user_id, payload.new_password)


@router.post(
    "/users/{user_id}/profile",
    response_model=AdminUserProfileResponse,
    summary="Create profile for a user",
    description=("Creates a new user profile. Requires admin privileges."),
    responses={
        200: {"description": "The user profile was successfully created."},
        401: {"description": "Unauthorized. The user is not authenticated."},
        404: {"description": "Not found. The user does not exist."},
        409: {"description": "Conflict. The profile already exists."},
        403: {
            "description": (
                "Forbidden. The user does not have admin privileges."
            )
        },
    },
)
async def admin_create_profile(
    user_id: int,
    payload: AdminUserProfileCreateSchema,
    service: Annotated[
        AdminUserProfileService, Depends(get_admin_user_profile_service)
    ],
):
    """Creates a new user profile.

    :param user_id: The ID of the user whose profile to create.
    :param payload: A schema containing the profile's data.
    :param service: An instance of AdminUserProfileService.
    :return: The newly created user profile.
    :raises HTTPException: If the user is not found, if the profile already
        exists, or if the user does not have admin privileges.
    """
    return await service.create_profile(
        user_id, payload.model_dump(exclude_none=True)
    )


@router.patch(
    "/users/{user_id}/profile",
    response_model=AdminUserProfileResponse,
    summary="Update profile for a user",
    description=(
        "Updates an existing user profile. Requires admin privileges."
    ),
    responses={
        200: {"description": "The user profile was successfully updated."},
        401: {"description": "Unauthorized. The user is not authenticated."},
        404: {"description": "Not found. The user or profile does not exist."},
        403: {
            "description": (
                "Forbidden. The user does not have admin privileges."
            )
        },
    },
)
async def admin_update_profile(
    user_id: int,
    payload: AdminUserProfileUpdateSchema,
    service: Annotated[
        AdminUserProfileService, Depends(get_admin_user_profile_service)
    ],
):
    """Updates an existing user profile. Requires admin privileges.

    :param user_id: The ID of the user whose profile to update.
    :param payload: A dictionary containing the profile's updated data.
    :param service: An instance of AdminUserProfileService.
    :return: The updated user profile.
    :raises HTTPException: If the profile is not found.
    """
    return await service.update_profile(
        user_id, payload.model_dump(exclude_none=True)
    )


@router.delete(
    "/users/{user_id}/profile",
    summary="Delete profile for a user",
    description=(
        "Deletes an existing user profile. Requires admin privileges."
    ),
    responses={
        204: {"description": "The user profile was successfully deleted."},
        401: {"description": "Unauthorized. The user is not authenticated."},
        404: {"description": "Not found. The user or profile does not exist."},
        403: {
            "description": (
                "Forbidden. The user does not have admin privileges."
            )
        },
    },
    status_code=status.HTTP_204_NO_CONTENT,
)
async def admin_delete_profile(
    user_id: int,
    service: Annotated[
        AdminUserProfileService, Depends(get_admin_user_profile_service)
    ],
):
    """Deletes an existing user profile. Requires admin privileges.

    Parameters:
        user_id (int): The ID of the user whose profile to delete.

    Returns:
        None

    Raises:
        HTTPException: If the profile is not found or if the user does not have
        admin privileges.
    """
    return await service.delete_profile(user_id)
