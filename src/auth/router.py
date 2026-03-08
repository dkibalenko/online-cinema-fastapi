from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from auth.dependencies import get_auth_service, get_current_user
from auth.schemas import (
    ChangePasswordSchema,
    MessageResponseSchema,
    PasswordResetCompleteRequestSchema,
    PasswordResetRequestSchema,
    ResendActivationRequestSchema,
    TokenRefreshRequestSchema,
    TokenRefreshResponseSchema,
    UserActivationRequestSchema,
    UserLoginRequestSchema,
    UserLoginResponseSchema,
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
)
from auth.service import AuthService
from config import BaseAppSettings, get_settings
from rate_limiting import limiter
from users.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRegistrationResponseSchema,
    summary="User Registration",
    description="Registers a new user and sends an activation email.",
    responses = {
        201: {"description": "The user was successfully registered."},
        400: {
            "description": "Bad Request. The email is already registered or "
            "the input data is invalid."
        },
        409: {"description": "Conflict. The email is already registered."},
    },
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("3/minute")
async def register_user(
    request: Request,
    user_data: UserRegistrationRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> UserRegistrationResponseSchema:
    """Registers a new user and sends an activation email.

    Args:
        request (Request): The incoming request.
        user_data (UserRegistrationRequestSchema): The registration data
            containing the user's email and password.
        auth (AuthService): The authentication service.

    Returns:
        UserRegistrationResponseSchema: A response containing a success
        message.

    Raises:
        HTTPException: If the email is already registered or the input data
        is invalid.
    """
    return await auth.register_user(user_data)


@router.post(  # for a clickable activation link we need GET /activate?token=..
    "/activate",
    response_model=MessageResponseSchema,
    summary="User Activation",
    description="Activates the user account using the activation token.",
    responses = {
        200: {"description": "The user account was successfully activated."},
        400: {"description": "Bad Request. The token is invalid or expired."},
        404: {"description": "Not Found. The token was not found."},
    },
    status_code=status.HTTP_200_OK,
)
async def activate_account(
    activation_data: UserActivationRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponseSchema:
    # user must POST email + token manually
    """Activates a user account based on the activation token.

    Args:
        activation_data (UserActivationRequestSchema): The activation data
            containing the user's email and activation token.
        auth (AuthService): The authentication service.

    Returns:
        MessageResponseSchema: A response containing a success message.

    Raises:
        HTTPException: If the activation token is invalid or expired, or
            if the user account is already active.
    """
    return await auth.activate_account(activation_data)


@router.post(
    "/activate/resend",
    response_model=MessageResponseSchema,
    summary="Resend Activation Token",
    description="Resends the activation token to the user's email address.",
    responses = {
        200: {
            "description": "The activation token was resent to the user email."
        },
        400: {"description": "Bad Request. The email is invalid."},
        404: {"description": "Not Found. The user is not found."},
    },
    status_code=status.HTTP_200_OK,
)
@limiter.limit("3/minute")
async def resend_activation(
    request: Request,
    data: ResendActivationRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponseSchema:
    """Resends the activation token to the user's email address.

    Args:
        request (Request): The HTTP request object.
        data (ResendActivationRequestSchema): The email address of the user to
            send the activation token to.
        auth (AuthService): The authentication service.

    Returns:
        MessageResponseSchema: A response containing a success message.

    Raises:
        HTTPException: If the email is invalid.
        HTTPException: If the user is not found.
    """
    return await auth.resend_activation_token(data)


@router.post(
    "/login",
    response_model=UserLoginResponseSchema,
    summary="User login",
    description="Logs in the user and returns an access token.",
    responses = {
        200: {"description": "The user was successfully logged in."},
        400: {
            "description": "Bad Request. The email or password is incorrect."
        },
        401: {"description": "Unauthorized. The user is not authenticated."},
        403: {"description": "Forbidden. The user account is not activated."},
    },
    status_code=status.HTTP_200_OK,
)
@limiter.limit("5/minute")
async def login_user(
    request: Request,
    login_data: UserLoginRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[BaseAppSettings, Depends(get_settings)],
) -> UserLoginResponseSchema:
    """Logs in the user and returns an access token.

    Args:
        request (Request): The HTTP request object.
        login_data (UserLoginRequestSchema): The login data containing the
            user's email and password.
        auth (AuthService): The authentication service.
        settings (BaseAppSettings): The application settings.

    Returns:
        UserLoginResponseSchema: A response containing an access token.

    Raises:
        HTTPException: If the email or password is incorrect.
        HTTPException: If the user is not authenticated.
        HTTPException: If the user account is not activated.
    """
    return await auth.login_user(login_data, settings)


@router.post(
    "/refresh",
    response_model=TokenRefreshResponseSchema,
    summary="Refresh Access Token",
    description="Refreshes the access token using the refresh token.",
    responses = {
        200: {"description": "The access token was successfully refreshed."},
        400: {"description": "Bad Request. The refresh token is invalid."},
        401: {"description": "Unauthorized. The user is not authenticated."},
        404: {"description": "Not Found. The user is not found."},
    },
    status_code=status.HTTP_200_OK,
)
@limiter.limit("20/minute")
async def refresh_access_token(
    request: Request,
    token_data: TokenRefreshRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenRefreshResponseSchema:
    """Refreshes the access token using the refresh token.

    Args:
        request (Request): The HTTP request object.
        token_data (`TokenRefreshRequestSchema`): The refresh token data.
        auth (`AuthService`): The authentication service.

    Returns:
        `TokenRefreshResponseSchema`: A response containing the new
        access token.

    Raises:
        HTTPException: If the refresh token is invalid, expired, or doesn't
            belong to the user.
        HTTPException: If the user is not found.
    """
    return await auth.refresh_access_token(token_data)


@router.post(
    "/logout",
    response_model=MessageResponseSchema,
    summary="Logout user",
    description="Logs out the user by invalidating the refresh token.",
    responses = {
        200: {"description": "The user was successfully logged out."},
        400: {"description": "Bad Request. The token is invalid."},
        401: {"description": "Unauthorized. The user is not authenticated."},
    },
    status_code=status.HTTP_200_OK,
)
@limiter.limit("20/minute")
async def logout_user(
    request: Request,
    token_data: TokenRefreshRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponseSchema:
    """Logs out the user by invalidating the refresh token.

    Args:
        request (Request): The HTTP request object.
        token_data (TokenRefreshRequestSchema): The refresh token data
        containing the refresh token.
        auth (AuthService): The authentication service.

    Returns:
        MessageResponseSchema: A response containing a success message.

    Raises:
        HTTPException: If the refresh token is invalid.
        HTTPException: If the user is not authenticated.
    """
    return await auth.logout_user(token_data)


@router.post(
    "/password-reset/request",
    response_model=MessageResponseSchema,
    summary="Request Password Reset Token",
    description="Sends a password reset token to the user's email address.",
    responses = {
        200: {
            "description": "The password reset token sent to the user's email."
        },
        400: {"description": "Bad Request. The email is invalid."},
    },
    status_code=status.HTTP_200_OK,
)
@limiter.limit("3/minute")
async def request_password_reset_token(
    request: Request,
    data: PasswordResetRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponseSchema:
    """Sends a password reset token to the user's email address.

    Args:
        request (Request): The HTTP request object.
        data (PasswordResetRequestSchema): The email address of the user to
        send the password reset token to.
        auth (AuthService): The authentication service.

    Returns:
        MessageResponseSchema: A response containing a success message.

    Raises:
        HTTPException: If the email is invalid.
    """
    return await auth.request_password_reset(data)


@router.post(
    "/password-reset/complete",
    response_model=MessageResponseSchema,
    summary="Complete Password Reset",
    description="Resets the user's password using a password reset token.",
    responses = {
        200: {"description": "The password was successfully reset."},
        400: {"description": "Bad Request. The token is invalid or expired."},
        404: {"description": "Not Found. The token was not found."},
    },
    status_code=status.HTTP_200_OK,
)
async def complete_password_reset(
    data: PasswordResetCompleteRequestSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponseSchema:
    """Resets the user's password using a password reset token.

    Args:
        data (PasswordResetCompleteRequestSchema): The password reset
            complete request data containing the reset token and new password.
        auth (AuthService): The authentication service.

    Returns:
        MessageResponseSchema: A response containing a success message.

    Raises:
        HTTPException: If the reset token is invalid, expired, or doesn't
            belong to the user.
        HTTPException: If the user is not found.
        HTTPException: If the password update fails due to a security
            error.
    """
    return await auth.reset_password(data)


@router.post(
    "/password-change",
    response_model=MessageResponseSchema,
    summary="Change Password",
    description="Changes the password for the currently authenticated user.",
    responses = {
        200: {"description": "The password was successfully changed."},
        403: {"description": "Forbidden. The user is not authenticated."},
        400: {"description": "Bad Request. The old password is incorrect."},
    },
    status_code=status.HTTP_200_OK,
)
async def change_password(
    user: Annotated[User, Depends(get_current_user)],
    data: ChangePasswordSchema,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponseSchema:
    """Changes the password for the currently authenticated user.

    Args:
        user (User): The currently authenticated user.
        data (ChangePasswordSchema): The new password and old password.
        auth (AuthService): The authentication service.

    Returns:
        MessageResponseSchema: A response containing a success message.
    """
    return await auth.change_password(user, data)
