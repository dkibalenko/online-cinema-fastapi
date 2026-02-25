from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from users.models import User, UserProfile


class AdminUserProfileRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user(self, user_id: int) -> User | None:
        """
        Retrieves a user by their ID.

        :param user_id: The ID of the user to retrieve.
        :return: The user with the given ID, or None if no user is found.
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_profile(self, user_id: int) -> UserProfile | None:
        """
        Retrieves a user's profile by their ID.

        :param user_id: The ID of the user whose profile to retrieve.
        :return: The user's profile, or None if no profile is found.
        """
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_profile(self, user: User, data: dict) -> UserProfile:
        """
        Creates a new user profile.

        :param user: The user to associate the profile with.
        :param data: A dictionary containing the profile's data.
        :return: The newly created user profile.
        """
        profile = UserProfile(user_id=user.id, **data)
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def update_profile(
        self,
        profile:
        UserProfile,
        data: dict
    ) -> UserProfile:
        """
        Updates an existing user profile.

        :param profile: The user profile to update.
        :param data: A dictionary containing the profile's updated data.
        :return: The updated user profile.
        """
        for key, value in data.items():
            setattr(profile, key, value)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def delete_profile(self, profile: UserProfile):
        """
        Deletes an existing user profile.

        :param profile: The user profile to delete.
        """
        await self.db.delete(profile)
        await self.db.commit()
