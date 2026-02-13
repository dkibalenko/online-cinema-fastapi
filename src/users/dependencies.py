from auth.dependencies import get_jwt_auth_manager
from fastapi import HTTPException, status, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from users.repository import UserRepository
from users.service import UserService
from storages.dependencies import get_s3_storage_client
from storages.interfaces import S3StorageInterface


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_token(request: Request) -> str:
    """
    Extracts the Bearer token from the Authorization header.

    :param request: FastAPI Request object.
    :return: Extracted token string.
    :raises HTTPException: If Authorization header is missing or invalid.
    """
    authorization: str = request.headers.get("Authorization")

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'"
        )

    return token


def get_users_service(
    users: UserRepository = Depends(get_user_repository),
    jwt = Depends(get_jwt_auth_manager),
    s3_client: S3StorageInterface = Depends(get_s3_storage_client)
) -> UserService:
    return UserService(
        users=users,
        jwt=jwt,
        s3_client=s3_client
    )
