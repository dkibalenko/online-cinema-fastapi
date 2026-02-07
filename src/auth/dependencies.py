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
from auth.repository import UserRepository
from config import BaseAppSettings
from auth.service import AuthService
from auth.interfaces import EmailSenderInterface
from auth.email_manager import EmailSender


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """
    Retrieves an instance of the `UserRepository` class based on the provided
    database session.

    The `UserRepository` provides methods for performing CRUD operations
    on users.

    Args:
        db (AsyncSession): The database session to use for database operations.

    Returns:
        `UserRepository`: An instance of the `UserRepository` class.
    """
    return UserRepository(db)


def get_email_sender(settings: BaseAppSettings = Depends(get_settings)):
    return EmailSender(
        hostname=settings.SMTP_SERVER,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        use_tls=settings.SMTP_USE_TLS,
        template_dir=settings.PATH_TO_EMAIL_TEMPLATES_DIR,
        activation_email_template_name=settings.ACTIVATION_EMAIL_TEMPLATE_NAME,
        activation_complete_email_template_name=settings.ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME,
        password_email_template_name=settings.PASSWORD_RESET_TEMPLATE_NAME,
        password_complete_email_template_name=settings.PASSWORD_RESET_COMPLETE_TEMPLATE_NAME,
    )

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
    token: str = Depends(oauth2_scheme),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Extracts and returns the authenticated user based on the access token.
    """
    import pdb; pdb.set_trace()
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

    user_id = payload.get("user_id")

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


def get_auth_service(
    users: UserRepository = Depends(get_user_repository),
    jwt = Depends(get_jwt_auth_manager),
    email_sender: EmailSenderInterface = Depends(get_email_sender),
) -> AuthService:
    """
    Dependency factory that returns an instance of AuthService.

    The AuthService instance is created with the following dependencies:
    - users: UserRepository instance
    - jwt: JWTAuthManager instance
    - email_sender: EmailSenderInterface instance

    Returns:
        AuthService: An instance of AuthService
    """
    return AuthService(
        users=users,
        jwt=jwt,
        email_sender=email_sender,
    )
