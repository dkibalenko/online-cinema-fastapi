from datetime import datetime, timezone
from typing import cast

from fastapi import status, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from exceptions import BaseSecurityError
from auth.models import ActivationToken, PasswordResetToken, RefreshToken, User
from auth.schemas import (
    MessageResponseSchema,
    UserRegistrationRequestSchema,
    UserActivationRequestSchema,
    UserLoginRequestSchema,
    UserLoginResponseSchema,
    TokenRefreshRequestSchema,
    TokenRefreshResponseSchema,
    ResendActivationRequestSchema,
    PasswordResetRequestSchema,
    PasswordResetCompleteRequestSchema
)
from auth.interfaces import JWTAuthManagerInterface, EmailSenderInterface
from auth.repository import UserRepository
from logger_config import get_logger
from config import BaseAppSettings

log = get_logger()


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        jwt: JWTAuthManagerInterface,
        email_sender: EmailSenderInterface
    ):
        self.users = users
        self.jwt = jwt
        self.email_sender = email_sender

    # registration, login, refresh, logout will go here
    async def register_user(
        self,
        user_data: UserRegistrationRequestSchema
    ) -> User:
        """
        Registers a new user based on the provided registration data.

        Args:
            user_data (UserRegistrationRequestSchema): The registration data

        Returns:
            User: The newly created user

        Raises:
            HTTPException: If a user with the same email already exists
            HTTPException: If the default user group is not found
            HTTPException: If an error occurs during user creation
        """
        log.info(f"Registration attempt for {user_data.email}")

        # 1. Check email uniqueness
        existing_user = await self.users.get_by_email(user_data.email)

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A user with email '{user_data.email}' already exists."
            )

        # 2. Get default group
        group = await self.users.get_default_user_group()

        if not group:
            raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default user group not found."
        )

        # 3. Create user + activation token
        try:
            user = User.create(
                email=str(user_data.email),
                raw_password=user_data.password,
                group_id=group.id
            )
            self.users.add(user)
            await self.users.flush()

            token = ActivationToken(user_id=user.id)
            self.users.add(token)

            await self.users.commit()
            # here, token is set right away before flush() & is available, so,
            # no need to query again. Also, refresh(user) need not be called,
            # since atts are valid after commit (expire_on_commit=False)
        except SQLAlchemyError:
            await self.users.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred during user creation."
            )

        # 4. Send activation email
        # activation_link = f"{settings.FRONTEND_URL}/activate?token={token.token}"
        activation_link = (
            f"http://127.0.0.1:8000/api/v1/cinema/auth/activate?"
            f"token={token.token}"
        )
        await self.email_sender.send_activation_email(
            email=user.email,
            activation_link=activation_link
        )

        log.info(f"Registration successful for {user_data.email}")

        return user

    async def activate_account(
        self,
        activation_data: UserActivationRequestSchema,
    ) -> MessageResponseSchema:
        """
        Activate a user account based on the activation token.

        Args:
            activation_data (UserActivationRequestSchema): The activation data
                containing the user's email and activation token.

        Returns:
            MessageResponseSchema: A response containing a success message.

        Raises:
            HTTPException: If the activation token is invalid or expired, or
                if the user account is already active.
        """
        log.info(f"Activation attempt for {activation_data.email}")

        # 1. Fetch token + user
        token_record = await self.users.get_activation_token_record(
            email=activation_data.email,
            token=activation_data.token
        )

        now_utc = datetime.now(timezone.utc)

        # 2. Validate token existence and expiration
        if not token_record or token_record.expires_at < now_utc:
            if token_record:
                await self.users.delete_activation_token(token_record)
                await self.users.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired activation token."
            )

        user = token_record.user

        # 3. Prevent double activation
        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is already active."
            )

        # 4. Activate user + delete token in one commit
        user.is_active = True
        await self.users.delete_activation_token(token_record)
        await self.users.commit()

        # 5. Send confirmation email
        login_link = "http://127.0.0.1:8000/api/v1/cinema/auth/login"

        await self.email_sender.send_activation_complete_email(
            email=str(user.email),
            login_link=login_link
        )

        log.info(f"User {user.email} activated successfully")

        return MessageResponseSchema(
            message="Account activated successfully."
        )

    async def resend_activation_token(
        self,
        email_data: ResendActivationRequestSchema
    ) -> MessageResponseSchema:
        log.info(f"Resend activation attempt for {email_data.email}")

        user = await self.users.get_by_email(email_data.email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is already active."
            )
        
        # Delete old token if exists
        old_token = await self.users.get_activation_token_by_user_id(user.id)
        if old_token:
            await self.users.delete_activation_token(old_token)

        # Create new token
        new_token = ActivationToken(user_id=cast(int, user.id))
        self.users.add(new_token)
        await self.users.commit()

        # Send email
        activation_link = (
            f"http://127.0.0.1:8000/api/v1/cinema/auth/activate?"
            f"token={new_token.token}"
        )

        await self.email_sender.send_activation_email(
            email=user.email,
            activation_link=activation_link
        )

        log.info(f"Activation token resent for {user.email}")

        return MessageResponseSchema(
            message="A new activation link has been sent to your email."
        )

    async def login_user(
        self,
        login_data: UserLoginRequestSchema,
        settings: BaseAppSettings,
    ) -> UserLoginResponseSchema:
        """
        Login a user and generate an access token and refresh token.

        Args:
            login_data (`UserLoginRequestSchema`): The login data containing the user's email and password.
            settings (`BaseAppSettings`): The application settings.

        Returns:
            `UserLoginResponseSchema`: A response containing the access token and refresh token.

        Raises:
            HTTPException: If the user credentials are invalid, or if the user account is not activated.
        """
        log.info(f"Login attempt for {login_data.email}")

        user = await self.users.get_by_email(login_data.email)

        # 1. Validate user credentials
        if not user or not user.verify_password(login_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not activated.",
            )

        # 2. Generate refresh token (JWT)
        jwt_refresh_token = self.jwt.create_refresh_token({"user_id": user.id})

        # 3. Store refresh token in DB
        try:
            async with self.users.db.begin():
                refresh_token = RefreshToken.create(
                    user_id=user.id,
                    days_valid=settings.LOGIN_TIME_DAYS,
                    token=jwt_refresh_token
                )
                self.users.add(refresh_token)
        except SQLAlchemyError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while processing the login request.",
            )

        # 4. Generate access token
        jwt_access_token = self.jwt.create_access_token({"user_id": user.id})

        log.info(f"User {user.email} logged in successfully")

        return UserLoginResponseSchema(
            access_token=jwt_access_token,
            refresh_token=jwt_refresh_token
        )

    async def refresh_access_token(
        self,
        token_data: TokenRefreshRequestSchema
    ) -> TokenRefreshResponseSchema:
        """
        Refreshes an access token given a valid refresh token.

        Args:
            token_data (`TokenRefreshRequestSchema`): The refresh token data containing the refresh token.

        Returns:
            `TokenRefreshResponseSchema`: A response containing the new access token and optionally the new refresh token.

        Raises:
            HTTPException: If the refresh token is invalid, expired, or doesn't belong to the user.
            HTTPException: If the user is not found.
        """
        log.info("Refreshing access token...")

        # 1. Decode refresh token
        try:
            decoded = self.jwt.decode_refresh_token(
                token_data.refresh_token
            )
            user_id = decoded.get("user_id")
        except BaseSecurityError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            )

        # 2. Validate refresh token exists in DB
        refresh_token_record = await self.users.get_refresh_token_record(
            token=token_data.refresh_token
        )

        if not refresh_token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found.",
            )

        # 3. Validate expiration
        now_utc = datetime.now(timezone.utc)

        if refresh_token_record.expires_at < now_utc:
            await self.users.delete_refresh_token(refresh_token_record)
            await self.users.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired.",
            )

        # 4. Validate user
        user = await self.users.get_by_id(user_id=user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        # 5. Validate refresh token belongs to this user(ownership check)
        if refresh_token_record.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token does not belong to this user.",
            )
        
        # 6. Rotate refresh token
        # new_refresh_jwt = self.jwt.create_refresh_token({"user_id": user_id})
        # refresh_token_record.token = new_refresh_jwt

        # 7. Generate new access token
        access_token = self.jwt.create_access_token({"user_id": user_id})

        log.info("Access token refreshed successfully")

        return  TokenRefreshResponseSchema(
            access_token=access_token,
            # refresh_token=new_refresh_jwt,
        )

    async def logout_user(
        self,
        token_data: TokenRefreshRequestSchema
    ) -> MessageResponseSchema:
        """
        Logs out a user based on the provided refresh token.

        Args:
            token_data (`TokenRefreshRequestSchema`): The refresh token data containing the refresh token.

        Returns:
            `MessageResponseSchema`: A response containing a success message.

        Raises:
            HTTPException: If the refresh token is invalid, expired, or doesn't belong to the user.
            HTTPException: If the user is not found.
        """
        log.info("Logout attempt...")

        # 1. Decode refresh token
        try:
            decoded = self.jwt.decode_refresh_token(
                token_data.refresh_token
            )
            user_id = decoded.get("user_id")
        except BaseSecurityError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            )

        # 2. Find refresh token in DB
        refresh_token_record = await self.users.get_refresh_token_record(
            token=token_data.refresh_token
        )

        if not refresh_token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found.",
            )

        # 3. Ownership check
        if refresh_token_record.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token does not belong to this user.",
            )

        # 4. Delete refresh token
        await self.users.delete_refresh_token(refresh_token_record)
        await self.users.commit()

        log.info(f"User {user_id} logged out successfully")

        return MessageResponseSchema(message="Logged out successfully.")

    async def request_password_reset(
        self,
        data: PasswordResetRequestSchema
    ) -> MessageResponseSchema:
        """
        Requests a password reset for a user with the given email.

        Args:
            data (`PasswordResetRequestSchema`): The password reset request data containing the user's email.

        Returns:
            `MessageResponseSchema`: A response containing a success message.

        Raises:
            HTTPException: If an error occurs during password reset request.
        """
        log.info(f"Password reset request for {data.email}")

        user = await self.users.get_by_email(data.email)

        if not user or not user.is_active:
            # Do NOT reveal whether the email exists
            return MessageResponseSchema(
                message=(
                    "If this email is registered, a reset link has been sent."
                )
            )

        old_token = await self.users.get_password_reset_token_by_user_id(
            user.id
        )
        try:
            async with self.users.db.begin():
                # Delete old token
                if old_token:
                    await self.users.delete_password_reset_token(old_token)

                # Create new token
                reset_token = PasswordResetToken(user_id=cast(int, user.id))
                self.users.add(reset_token)
        except SQLAlchemyError as error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(error),
            )

        reset_password_link = (
                f"http://127.0.0.1:8000/api/v1/cinema/auth/reset-password/"
                f"complete?token={reset_token.token}"
            )

        # Send email
        await self.email_sender.send_password_reset_email(
            email=user.email,
            reset_link=reset_password_link
        )

        log.info(f"Password reset link sent to {user.email}")

        return MessageResponseSchema(
            message=(
                "If this email is registered, a reset link has been sent."
            )
        )

    async def reset_password(
        self,
        data: PasswordResetCompleteRequestSchema
    ) -> MessageResponseSchema:
        """
        Resets the password for a user with the given reset token.

        Args:
            data (`PasswordResetCompleteRequestSchema`): The password reset complete request data containing the reset token and new password.

        Returns:
            `MessageResponseSchema`: A response containing a success message.

        Raises:
            HTTPException: If the reset token is invalid, expired, or doesn't belong to the user.
            HTTPException: If the user is not found.
            HTTPException: If the password update fails due to a security error.
        """
        log.info("Password reset attempt...")

        # 1. Validate token
        # Look up the token directly in the DB
        token_record = await self.users.get_password_reset_token(data.token)

        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token."
            )

        # 2. Validate token expiration
        if token_record.expires_at < datetime.now(timezone.utc):
            async with self.users.db.begin():
                await self.users.delete_password_reset_token(token_record)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token expired."
            )

        # 3. Validate user
        # Load the user from the token
        user = await self.users.get_by_id(token_record.user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        # 4. Update password + delete token
        try:
            async with self.users.db.begin():
                user.password(data.password)
                await self.users.delete_password_reset_token(token_record)
        except BaseSecurityError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            )

        # 6. Send confirmation email
        login_link = "http://127.0.0.1:8000/api/v1/cinema/auth/login"

        await self.email_sender.send_password_reset_complete_email(
            email=user.email,
            login_link=login_link
        )

        log.info("Password reset successful")

        return MessageResponseSchema(
            message="Password has been reset successfully."
        )
