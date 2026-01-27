# src/auth/service.py
from sqlalchemy.ext.asyncio import AsyncSession

from auth.models import User, RefreshToken
from auth.utils import hash_password, verify_password
from auth.schemas import (
    UserRegistrationRequestSchema,
    UserLoginRequestSchema,
)
from auth.token_manager import JWTAuthManager


class AuthService:
    def __init__(self, db: AsyncSession, jwt: JWTAuthManager):
        self.db = db
        self.jwt = jwt

    # registration, login, refresh, logout will go here
