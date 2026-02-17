from typing import Annotated

from fastapi import APIRouter, Depends, status, Request

from rate_limiting import limiter
from config import BaseAppSettings, get_settings
from auth.dependencies import get_auth_service, get_current_user
from auth.service import AuthService
from auth.models import User
from auth.schemas import (
    MessageResponseSchema,
    UserActivationRequestSchema,
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
    UserLoginRequestSchema,
    UserLoginResponseSchema,
    TokenRefreshRequestSchema,
    TokenRefreshResponseSchema,
    ResendActivationRequestSchema,
    PasswordResetRequestSchema,
    PasswordResetCompleteRequestSchema,
    ChangePasswordSchema,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register/",
    response_model=UserRegistrationResponseSchema,
    summary="User Registration",
    status_code=status.HTTP_201_CREATED
)
@limiter.limit("3/minute")
async def register_user(
    request: Request,
    user_data: UserRegistrationRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> UserRegistrationResponseSchema:
    user = await auth.register_user(user_data)
    return user


@router.post(  # for a clickable activation link we need GET /activate?token=...
    "/activate/",
    response_model=MessageResponseSchema,
    summary="User Activation",
    status_code=status.HTTP_200_OK
)
async def activate_account(
    activatation_data: UserActivationRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponseSchema:
    # user must POST email + token manually
    return await auth.activate_account(activatation_data)


@router.post(
    "/activate/resend/",
    response_model=MessageResponseSchema,
    summary="Resend Activation Token",
    status_code=status.HTTP_200_OK
)
@limiter.limit("3/minute")
async def resend_activation(
    request: Request,
    data: ResendActivationRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)]
) -> MessageResponseSchema:
    return await auth.resend_activation_token(data)


@router.post(
    "/login/",
    response_model=UserLoginResponseSchema,
    summary="User login",
    status_code=status.HTTP_200_OK
)
@limiter.limit("5/minute")
async def login_user(
    request: Request,
    login_data: UserLoginRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[BaseAppSettings, Depends(get_settings)]
) -> UserLoginResponseSchema:
    return await auth.login_user(login_data, settings)


@router.post(
    "/refresh/",
    response_model=TokenRefreshResponseSchema,
    summary="Refresh Access Token",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("20/minute")
async def refresh_access_token(
    request: Request,
    token_data: TokenRefreshRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)]
) -> TokenRefreshResponseSchema:
    return await auth.refresh_access_token(token_data)


@router.post(
    "/logout/",
    response_model=MessageResponseSchema,
    summary="Logout user",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("20/minute")
async def logout_user(
    request: Request,
    token_data: TokenRefreshRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)]
) -> MessageResponseSchema:
    return await auth.logout_user(token_data)


@router.post(
    "/password-reset/request/",
    response_model=MessageResponseSchema,
    summary="Request Password Reset Token",
    status_code=status.HTTP_200_OK
)
@limiter.limit("3/minute")
async def request_password_reset_token(
    request: Request,
    data: PasswordResetRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)]
) -> MessageResponseSchema:
    return await auth.request_password_reset(data)


@router.post(
    "/password-reset/complete/",
    response_model=MessageResponseSchema,
    summary="Complete Password Reset",
    status_code=status.HTTP_200_OK
)
async def complete_password_reset(
    data: PasswordResetCompleteRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)]
) -> MessageResponseSchema:
    return await auth.reset_password(data)


@router.post(
    "/password-change/",
    response_model=MessageResponseSchema,
    summary="Change Password",
    status_code=status.HTTP_200_OK
)
async def change_password(
    user: Annotated[User, Depends(get_current_user)],
    data: ChangePasswordSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)]
) -> MessageResponseSchema:
    return await auth.change_password(user, data)
