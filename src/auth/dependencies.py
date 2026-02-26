from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import get_settings, BaseAppSettings
from database import get_db
from logger_config import get_logger
from exceptions import InvalidTokenError, TokenExpiredError
from users.models import User, UserGroupEnum
from auth.interfaces import JWTAuthManagerInterface
from auth.token_manager import JWTAuthManager
from auth.repository import AuthRepository
from auth.service import AuthService
from notifications.interfaces import EmailSenderInterface
from notifications.dependencies import get_auth_email_sender


bearer_scheme = HTTPBearer()

log = get_logger()


def get_auth_repository(db: AsyncSession = Depends(get_db)) -> AuthRepository:
    return AuthRepository(db)


def get_jwt_auth_manager(
    settings: BaseAppSettings = Depends(get_settings)
) -> JWTAuthManagerInterface:
    """
    Retrieves an instance of the `JWTAuthManager` class based on 
    the application settings which implements the `JWTAuthManagerInterface`.

    The manager is configured with the secret keys for access & refresh tokens
    and JWT signing algorithm defined in the settings.

    Args:
        `settings` (BaseAppSettings): The application settings.

    Returns:
        `JWTAuthManager`: An instance of the `JWTAuthManager` class.    
    """
    return JWTAuthManager(
        secret_key_access=settings.JWT_SECRET_KEY_ACCESS.get_secret_value(),
        secret_key_refresh=settings.JWT_SECRET_KEY_REFRESH.get_secret_value(),
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Extracts and returns the authenticated user based on the access token.
    """
    token = credentials.credentials

    try:
        payload = jwt_manager.decode_access_token(token)
    except TokenExpiredError:
        log.error("Access token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
        )
    except InvalidTokenError:
        log.error("Invalid access token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

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
    except (TypeError, ValueError):
        log.error("Invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    result = await db.execute(select(User).where(User.id == user_id_int))
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
    """
    Dependency factory ensuring the current user has one of the allowed roles.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role(UserGroupEnum.ADMIN))])
        @router.post("/movies", dependencies=[Depends(require_role(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))])
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
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
    auth: AuthRepository = Depends(get_auth_repository),
    jwt = Depends(get_jwt_auth_manager),
    email_sender: EmailSenderInterface = Depends(get_auth_email_sender)
) -> AuthService:
    return AuthService(
        auth=auth,
        jwt=jwt,
        email_sender=email_sender
    )
