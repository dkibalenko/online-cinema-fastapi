from typing import Annotated

from auth.dependencies import get_auth_service
from auth.service import AuthService
from fastapi import APIRouter, Depends, status

from auth.schemas import (
    MessageResponseSchema,
    UserActivationRequestSchema,
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


@router.post(
    "/activate/",
    response_model=MessageResponseSchema,
    summary="User Activation",
    status_code=status.HTTP_200_OK
)
async def activate_account(
    activatation_data: UserActivationRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponseSchema:
    message = await auth.activate_account(activatation_data)
    return message
