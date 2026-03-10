from fastapi import HTTPException, status

from logger_config import get_logger
from users.admin.repositories.users import AdminUserRepository
from users.admin.schemas import UserFilterParams
from users.models import User, UserGroupEnum

log = get_logger()


class AdminUserService:
    def __init__(self, repo: AdminUserRepository):
        self.repo = repo

    async def list_filtered_users(
        self, filters: UserFilterParams
    ) -> list[User]:
        """Retrieves a list of users filtered by the given parameters.

        :param filters: A UserFilterParams object containing filters to apply.
        :return: A list of User objects that match the given filters.
        """
        log.info("Retrieving list of filtered users.")
        return await self.repo.filter_users(filters)

    async def update_group(self, user_id: int, group: UserGroupEnum):
        """Updates a user's group.

        :param user_id: The ID of the user to update.
        :param group: The new group for the user.

        :return: The updated user.
        """
        log.info(f"Updating group for user with ID {user_id} to {group}.")
        user = await self.repo.get_user(user_id)
        if not user:
            log.error(f"User with ID {user_id} not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        group_obj = await self.repo.get_group(group)
        if not group_obj:
            log.error(f"Group {group} not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
            )

        return await self.repo.update_group(user, group_obj)

    async def activate_user(self, user_id: int):
        """Activates a user account, i.e. sets their is_active flag to True.

        :param user_id: The ID of the user to activate.
        :return: The activated user.
        :raises HTTPException: If the user is not found.
        """
        log.info(f"Activating user with ID {user_id}.")
        user = await self.repo.get_user(user_id)
        if not user:
            log.error(f"User with ID {user_id} not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return await self.repo.activate_user(user)

    async def deactivate_user(self, user_id: int):
        """Deactivates a user account, i.e. sets their is_active flag to False.

        :param user_id: The ID of the user to deactivate.
        :return: The deactivated user.
        :raises HTTPException: If the user is not found.
        """
        log.info(f"Deactivating user with ID {user_id}.")
        user = await self.repo.get_user(user_id)
        if not user:
            log.error(f"User with ID {user_id} not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return await self.repo.deactivate_user(user)

    async def reset_password(self, user_id: int, new_password: str):
        """Resets the password for a user with the given ID.

        :param user_id: The ID of the user to reset the password for.
        :param new_password: The new password for the user.
        :return: The updated user.
        :raises HTTPException: If the user is not found.
        """
        log.info(f"Resetting password for user with ID {user_id}.")
        user = await self.repo.get_user(user_id)
        if not user:
            log.error(f"User with ID {user_id} not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        user.password = new_password  # triggers hashing + validation
        await self.repo.db.commit()
        await self.repo.db.refresh(user)
        log.info(f"Password for user with ID {user_id} has been reset.")
        return user
