from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auth.interfaces import JWTAuthManagerInterface
from auth.repository import AuthRepository
from auth.service import AuthService
from auth.token_manager import JWTAuthManager
from config import BaseAppSettings, get_settings
from database import get_db
from exceptions import InvalidTokenError, TokenExpiredError
from logger_config import get_logger
from notifications.dependencies import get_auth_email_sender
from notifications.interfaces import AuthEmailSenderInterface
from users.models import User, UserGroupEnum

bearer_scheme = HTTPBearer()

log = get_logger()


def get_auth_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthRepository:
    """Dependency factory that returns an instance of the `AuthRepository`.

    The repository is constructed using the provided async database session.

    :param db: An async database session.
    :return: An instance of the `AuthRepository` class.
    """
    return AuthRepository(db)


def get_jwt_auth_manager(
    settings: Annotated[BaseAppSettings, Depends(get_settings)],
) -> JWTAuthManagerInterface:
    """Retrieves an instance of the `JWTAuthManager` class.

    The manager is created based on the application settings which implements
    the `JWTAuthManagerInterface`.

    The manager is configured with the secret keys for access & refresh tokens
    and JWT signing algorithm defined in the settings.

    Args:
        settings: An instance of the `BaseAppSettings` class.

    Returns:
        `JWTAuthManager`: An instance of the `JWTAuthManager` class.
    """
    return JWTAuthManager(
        secret_key_access=settings.JWT_SECRET_KEY_ACCESS.get_secret_value(),
        secret_key_refresh=settings.JWT_SECRET_KEY_REFRESH.get_secret_value(),
        algorithm=settings.JWT_SIGNING_ALGORITHM,
    )


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials, Depends(bearer_scheme)
    ],
    jwt_manager: Annotated[
        JWTAuthManagerInterface, Depends(get_jwt_auth_manager)
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Extracts and returns an authenticated user based on the access token."""
    token = credentials.credentials

    try:
        payload = jwt_manager.decode_access_token(token)
    except TokenExpiredError as error:
        log.error("Access token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
        ) from error
    except InvalidTokenError as error:
        log.error("Invalid access token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        ) from error

    if payload.get("type") != "access":
        log.error("Invalid token type")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("user_id")

    if not user_id:
        log.error("Token payload missing user ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing user ID",
        )

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError) as error:
        log.error("Invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from error

    result = await db.execute(
        select(User)
        .options(selectinload(User.group))
        .where(User.id == user_id_int)
    )
    user = result.scalar_one_or_none()

    if not user:
        log.error("User not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        log.error("User account is not activated")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated",
        )

    return user


def require_role(*allowed_roles: UserGroupEnum):
    """Dependency factory.

    Checks if the current user has one of the allowed roles.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role(ADMIN))])
        @router.post("/movies", dependencies=[Depends(require_role(ADMIN))])
    """

    def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        # Check if user has any allowed role
        if not any(current_user.has_group(role) for role in allowed_roles):
            allowed = ", ".join(role.value for role in allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {allowed}",
            )
        return current_user

    return role_checker


def get_auth_service(
    auth: Annotated[AuthRepository, Depends(get_auth_repository)],
    jwt: Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)],
    email_sender: Annotated[
        AuthEmailSenderInterface, Depends(get_auth_email_sender)
    ],
) -> AuthService:
    """Dependency factory that returns an instance of the `AuthService`.

    :param auth: An instance of the `AuthRepository` class.
    :param jwt: An instance of the `JWTAuthManager` class.
    :param email_sender: An instance of the `AuthEmailSenderInterface` class.
    :return: An instance of the `AuthService` class.
    """
    return AuthService(auth=auth, jwt=jwt, email_sender=email_sender)
