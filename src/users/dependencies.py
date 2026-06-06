from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from storages.dependencies import get_s3_storage_client
from storages.interfaces import S3StorageInterface
from users.repository import UserRepository
from users.service import UserService


def get_user_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRepository:
    """Dependency factory that returns an instance of the UserRepository class.

    :param db: An async database session.
    :return: An instance of the UserRepository class.
    """
    return UserRepository(db)


def get_users_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
    s3_client: Annotated[S3StorageInterface, Depends(get_s3_storage_client)],
) -> UserService:
    """Dependency factory that returns an instance of the UserService class.

    :param users: An instance of the UserRepository class.
    :param s3_client: An instance of the S3StorageInterface class.
    :return: An instance of the UserService class.
    """
    return UserService(users=users, s3_client=s3_client)
