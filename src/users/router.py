from typing import Annotated

from fastapi import APIRouter, Depends, status, Request

from rate_limiting import limiter
from auth.dependencies import get_current_user
from users.dependencies import get_users_service, get_token
from users.service import UserService
from users.models import User
from auth.schemas import MessageResponseSchema
from users.schemas import (
    ProfileResponseSchema,
    ProfileCreationSchema,
    ProfileUpdateSchema
)


router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me/profile",
    response_model=ProfileResponseSchema,
    summary="Get current user's profile",
    description="Get current user's profile. Requires authentication.",
    responses={
        200: {"description": "The user profile was successfully retrieved."},
        401: {"description": "Unauthorized. The user is not authenticated."},
        404: {"description": "Not found. The user or profile does not exist."},
    },
    status_code=status.HTTP_200_OK,
)
@limiter.limit("10/minute")
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    users: Annotated[UserService, Depends(get_users_service)],
) -> ProfileResponseSchema:
    profile, avatar_url = await users.get_my_profile(current_user.id)

    return ProfileResponseSchema(
        id=profile.id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        gender=profile.gender,
        date_of_birth=profile.date_of_birth,
        info=profile.info,
        avatar=avatar_url,
        user_id=profile.user_id,
    )


@router.post(
    "/{user_id}/profile",
    response_model=ProfileResponseSchema,
    summary="User's profile creation",
    description=(
        "Create a profile for the user with the specified ID. "
        "Requires authentication."
    ),
    responses={
        201: {"description": "The user profile was successfully created."},
        400: {
            "description": (
                "Bad request. The provided data is invalid or "
                "the user already has a profile."
            )
        },
        401: {"description": "Unauthorized. The user is not authenticated."},
        403: {"description": (
            "Forbidden. The authenticated user does not have permission to "
            "create a profile for this user."
            )
        },
        404: {"description": "Not found. The user does not exist."},
    },
    status_code=status.HTTP_201_CREATED
)
@limiter.limit("3/minute")
async def create_user_profile(
    request: Request,
    user_id: int,  # is sent separately in the path
    data: Annotated[
        ProfileCreationSchema,
        Depends(ProfileCreationSchema.as_form)
    ],
    jwt_token: Annotated[str, Depends(get_token)],
    users: Annotated[UserService, Depends(get_users_service)],
) -> ProfileResponseSchema:
    profile, avatar_url = await users.create_user_profile(
        user_id,
        data,
        jwt_token
    )

    return ProfileResponseSchema(
        id=profile.id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        gender=profile.gender,
        date_of_birth=profile.date_of_birth,
        info=profile.info,
        avatar=avatar_url,
        user_id=profile.user_id
    )


@router.patch(
    "/me/profile",
    response_model=ProfileResponseSchema,
    summary="Update current user's profile",
    description="Update current user's profile. Requires authentication.",
    responses={
        200: {"description": "The user profile was successfully updated."},
        400: {"description": "Bad request. The provided data is invalid."},
        401: {"description": "Unauthorized. The user is not authenticated."},
        404: {"description": "Not found. The user or profile does not exist."},
    },
    status_code=status.HTTP_200_OK,
)
@limiter.limit("10/minute")
async def update_my_profile(
    request: Request,
    data: Annotated[ProfileUpdateSchema, Depends(ProfileUpdateSchema.as_form)],
    current_user: Annotated[User, Depends(get_current_user)],
    users: Annotated[UserService, Depends(get_users_service)],
    jwt_token: Annotated[str, Depends(get_token)],
):
    profile, avatar_url = await users.update_my_profile(
        current_user.id,
        data,
        jwt_token
    )

    return ProfileResponseSchema(
        id=profile.id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        gender=profile.gender,
        date_of_birth=profile.date_of_birth,
        info=profile.info,
        avatar=avatar_url,
        user_id=profile.user_id,
    )


@router.delete(
    "/me/profile",
    response_model=MessageResponseSchema,
    description="Delete current user's profile. Requires authentication.",
    responses={
        204: {"description": "The user profile was successfully deleted."},
        400: {"description": "Bad request. The user already has no profile."},
        401: {"description": "Unauthorized. The user is not authenticated."},
        404: {"description": "Not found. The user or profile does not exist."},
    },
    summary="Delete current user's profile",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    users: Annotated[UserService, Depends(get_users_service)],
    jwt_token: Annotated[str, Depends(get_token)],
) -> MessageResponseSchema:
    await users.delete_my_profile(current_user.id, jwt_token)
