from typing import Annotated

from fastapi import APIRouter, Depends, status, Request

from rate_limiting import limiter
from users.dependencies import get_users_service, get_token
from users.service import UserService
from users.models import User
from users.schemas import ProfileResponseSchema, ProfileCreationSchema


router = APIRouter()


@router.post(
    "/users/{user_id}/profile/",
    response_model=ProfileResponseSchema,
    summary="User's profile creation",
    status_code=status.HTTP_201_CREATED
)
@limiter.limit("3/minute")
async def create_user_profile(
    request: Request,
    user_id: int,
    data: Annotated[ProfileCreationSchema, Depends(ProfileCreationSchema.as_form)],
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
