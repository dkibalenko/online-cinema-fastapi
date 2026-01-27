# src/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import get_settings
from database import get_db
from exceptions import InvalidTokenError, TokenExpiredError
from auth.models import User, UserGroupEnum

from auth.interfaces import JWTAuthManagerInterface
from auth.token_manager import JWTAuthManager
from config import BaseAppSettings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_jwt_auth_manager(
    settings: BaseAppSettings = Depends(get_settings)
) -> JWTAuthManagerInterface:
    """
    Retrieves an instance of the JWTAuthManager class based on 
    the application settings which implements the JWTAuthManagerInterface.

    The manager is configured with the secret keys for access & refresh tokens
    and JWT signing algorithm defined in the settings.

    Args:
        settings (BaseAppSettings): The application settings.

    Returns:
        JWTAuthManager: An instance of the JWTAuthManager class.    
    """
    return JWTAuthManager(
        secret_key_access=settings.JWT_SECRET_KEY_ACCESS,
        secret_key_refresh=settings.JWT_SECRET_KEY_REFRESH,
        algorithm=settings.JWT_SIGNING_ALGORITHM
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Extracts and returns the authenticated user based on the access token.
    """
    try:
        payload = jwt_manager.decode_access_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing user ID",
        )

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not activated",
        )

    return user


def require_role(*allowed_roles: UserGroupEnum):
    """
    Dependency factory that ensures the current user has one of the
    allowed roles.
    
    Example:
        require_role(UserGroupEnum.ADMIN)
        require_role(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR)
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not any(current_user.has_group(role) for role in allowed_roles):
            allowed = ", ".join(role.value for role in allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {allowed}",
            )
        return current_user
    return role_checker
