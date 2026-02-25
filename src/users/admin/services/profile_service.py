from fastapi import HTTPException, status

from logger_config import get_logger
from users.admin.repositories.profiles import AdminUserProfileRepository


log = get_logger()


class AdminUserProfileService:
    def __init__(self, repo: AdminUserProfileRepository):
        self.repo = repo

    async def create_profile(self, user_id: int, data: dict):
        """
        Creates a new user profile.

        :param user_id: The ID of the user to associate the profile with.
        :param data: A dictionary containing the profile's data.
        :return: The newly created user profile.
        :raises HTTPException: If the user is not found or if the
            profile already exists.
        """
        log.info(f"Creating profile for user with ID {user_id}.")
        user = await self.repo.get_user(user_id)
        if not user:
            log.error(f"User with ID {user_id} not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        existing = await self.repo.get_profile(user_id)
        if existing:
            log.error(f"Profile for user with ID {user_id} already exists.")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Profile already exists"
            )

        return await self.repo.create_profile(user, data)

    async def update_profile(self, user_id: int, data: dict):
        """
        Updates an existing user profile.

        :param user_id: The ID of the user whose profile to update.
        :param data: A dictionary containing the profile's updated data.
        :return: The updated user profile.
        :raises HTTPException: If the profile is not found.
        """
        log.info(f"Updating profile for user with ID {user_id}.")
        profile = await self.repo.get_profile(user_id)
        if not profile:
            log.error(f"Profile for user with ID {user_id} not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )

        return await self.repo.update_profile(profile, data)

    async def delete_profile(self, user_id: int):
        """
        Deletes an existing user profile.

        :param user_id: The ID of the user whose profile to delete.
        :raises HTTPException: If the profile is not found.
        """
        log.info(f"Deleting profile for user with ID {user_id}.")
        profile = await self.repo.get_profile(user_id)
        if not profile:
            log.error(f"Profile for user with ID {user_id} not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )

        await self.repo.delete_profile(profile)
