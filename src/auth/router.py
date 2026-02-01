from typing import Annotated

from auth.dependencies import get_auth_service
from auth.service import AuthService
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

from auth.models import User, UserGroup, UserGroupEnum
from auth.schemas import (
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
)


router = APIRouter()


@router.post(
    "/register/",
    response_model=UserRegistrationResponseSchema,
    summary="User Registration",
    status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_data: UserRegistrationRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> UserRegistrationResponseSchema:
    user = await auth.register_user(user_data)
    return user
