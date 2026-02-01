from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import ActivationToken, User, RefreshToken
from auth.utils import hash_password, verify_password
from auth.schemas import (
    UserRegistrationRequestSchema,
    UserLoginRequestSchema,
)
from auth.interfaces import JWTAuthManagerInterface, EmailSenderInterface
from auth.repository import UserRepository


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
        except SQLAlchemyError:
            await self.users.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred during user creation."
            )

        # 4. Send activation email
        # activation_link = f"{settings.FRONTEND_URL}/activate?token={token.token}"
        activation_link = (
            f"http://127.0.0.1:8000/api/v1/accounts/activate?"
            f"token={token.token}"
        )
        await self.email_sender.send_activation_email(
            email=user.email,
            activation_link=activation_link
        )

        return user
