from datetime import datetime, timezone
from typing import cast

from fastapi import status, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from auth.models import ActivationToken, User
from auth.schemas import (
    MessageResponseSchema,
    UserRegistrationRequestSchema,
    UserActivationRequestSchema,
    UserLoginRequestSchema,
)
from auth.interfaces import JWTAuthManagerInterface, EmailSenderInterface
from auth.repository import UserRepository
from logger_config import get_logger

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
