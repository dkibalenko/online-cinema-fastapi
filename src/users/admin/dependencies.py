from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from users.admin.repositories.users import AdminUserRepository
from users.admin.repositories.profiles import AdminUserProfileRepository
from users.admin.services.user_service import AdminUserService
from users.admin.services.profile_service import AdminUserProfileService


def get_admin_user_repo(
    db: AsyncSession = Depends(get_db)
) -> AdminUserRepository:
    """
    Dependency factory that returns an instance of AdminUserRepository.

    :param db: An async database session.
    :return: An instance of AdminUserRepository.
    """
    return AdminUserRepository(db)


def get_admin_user_service(
    repo: AdminUserRepository = Depends(get_admin_user_repo)
) -> AdminUserService:
    """
    Dependency factory that returns an instance of AdminUserService.

    :param repo: An instance of AdminUserRepository.
    :return: An instance of AdminUserService.
    """
    return AdminUserService(repo)


def get_admin_user_profile_repo(
    db: AsyncSession = Depends(get_db)
) -> AdminUserProfileRepository:
    """
    Dependency factory that returns an instance of AdminUserProfileRepository.

    :param db: An async database session.
    :return: An instance of AdminUserProfileRepository.
    """
    return AdminUserProfileRepository(db)


def get_admin_user_profile_service(
    repo: AdminUserProfileRepository = Depends(get_admin_user_profile_repo)
) -> AdminUserProfileService:
    """
    Dependency factory that returns an instance of AdminUserProfileService.

    :param repo: An instance of AdminUserProfileRepository.
    :return: An instance of AdminUserProfileService.
    """
    return AdminUserProfileService(repo)
