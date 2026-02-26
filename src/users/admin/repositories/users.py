from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from users.models import User, UserGroup
from users.enums import UserGroupEnum
from users.admin.schemas import UserFilterParams


class AdminUserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def filter_users(
        self,
        filters: UserFilterParams
    ) -> list[User]:
        """
        Filters users based on the given parameters.

        :param filters: A UserFilterParams object containing filters to apply.
        :return: A list of User objects that match the given filters.
        """
        query = select(User)

        if filters.email:
            query = query.where(User.email.ilike(f"%{filters.email}%"))

        if filters.group:
            query = (
                query
                .join(User.group)
                .where(UserGroup.name == filters.group)
            )

        if filters.is_active is not None:
            query = query.where(User.is_active == filters.is_active)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_user(self, user_id: int) -> User | None:
        """
        Retrieves a user by their ID.

        :param user_id: The ID of the user to retrieve.
        :return: The user with the given ID, or None if no user is found.
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_group(self, group: UserGroupEnum) -> UserGroup | None:
        """
        Retrieves a user group by its name.

        :param group: The name of the user group to retrieve.
        :return: The user group with given name, or None if no group is found.
        """
        result = await self.db.execute(
            select(UserGroup).where(UserGroup.name == group)
        )
        return result.scalar_one_or_none()

    async def update_group(self, user: User, group: UserGroup):
        """
        Updates a user's group.

        :param user: The user to update.
        :param group: The new group for the user.
        :return: The updated user.
        """
        user.group = group
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def activate_user(self, user: User):
        """
        Activates a user account, i.e. sets their is_active flag to True.
        
        :param user: The user to activate.
        :return: The activated user.
        """
        user.is_active = True
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def deactivate_user(self, user: User):
        """
        Deactivates a user account, i.e. sets their is_active flag to False.

        :param user: The user to deactivate.
        :return: The deactivated user.
        """
        user.is_active = False
        await self.db.commit()
        await self.db.refresh(user)
        return user
