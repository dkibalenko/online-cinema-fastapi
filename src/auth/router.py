from typing import Annotated

from fastapi import APIRouter, Depends, status

from config import BaseAppSettings, get_settings
from auth.dependencies import get_auth_service
from auth.service import AuthService
from auth.schemas import (
    MessageResponseSchema,
    UserActivationRequestSchema,
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
    UserLoginRequestSchema,
    UserLoginResponseSchema,
    TokenRefreshRequestSchema,
    TokenRefreshResponseSchema,
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


@router.post(
    "/login/",
    response_model=UserLoginResponseSchema,
    summary="User login",
    status_code=status.HTTP_200_OK
)
async def login_user(
    login_data: UserLoginRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[BaseAppSettings, Depends(get_settings)]
) -> UserLoginResponseSchema:
    login_response = await auth.login_user(
        login_data, settings
    )
    return login_response


@router.post(
    "/refresh/",
    response_model=TokenRefreshResponseSchema,
    summary="Refresh Access Token",
    status_code=status.HTTP_200_OK,
)
async def refresh_access_token(
    token_data: TokenRefreshRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)]
) -> TokenRefreshResponseSchema:
    response = await auth.refresh_access_token(token_data)
    return response
