from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from logger_config import get_logger
from storages.exceptions import S3ConnectionError, S3FileUploadError
from storages.interfaces import S3StorageInterface
from users.enums import UserGroupEnum
from users.models import User, UserProfile
from users.repository import UserRepository
from users.schemas import ProfileCreationSchema, ProfileUpdateSchema

log = get_logger()


class UserService:
    def __init__(
        self,
        users: UserRepository,
        s3_client: S3StorageInterface,
    ):
        self.users = users
        self.s3_client = s3_client

    async def create_user_profile(
        self, user_id: int, data: ProfileCreationSchema, current_user: User
    ) -> tuple[UserProfile, str | None]:
        """Create user profile.

        :param user_id: The ID of the user for whom the profile is being
            created.
        :param data: The profile creation data.
        :param current_user: The authenticated user making the request.
        :return: A tuple containing the created UserProfile and the avatar
            URL (if uploaded).
        """
        log.info(f"Profile creation attempt | user_id={user_id}")

        # 1. Load target user
        target_user = await self.users.get_by_id_with_profile(user_id)

        if not target_user or not target_user.is_active:
            log.warning(f"User not found or inactive | user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive.",
            )

        # 2. Check permissions
        if current_user.id != user_id and not current_user.has_group(
            UserGroupEnum.ADMIN
        ):
            log.warning(
                f"Permission to edit profile denied | user_id={user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this profile.",
            )

        # 3. Check if profile already exists
        if target_user.profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile already exists.",
            )

        # 4. Upload avatar (optional)
        avatar_url = None
        file_name = None

        if data.avatar:
            contents = await data.avatar.read()

            ext = data.avatar.content_type.split("/")[-1].lower()
            ext = "jpg" if ext in ["jpeg", "jpg"] else "png"

            file_name = f"avatars/{user_id}_avatar.{ext}"

            try:
                await self.s3_client.upload_file(
                    file_name, contents, content_type="image/jpeg"
                )
                avatar_url = await self.s3_client.get_file_url(file_name)
                log.info(
                    f"Avatar upload | user_id={user_id} filename={file_name}"
                )
            except (S3ConnectionError, S3FileUploadError) as e:
                log.error(
                    f"Failed to upload avatar | user_id={user_id} "
                    f"filename={file_name}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to upload avatar. Please try again later.",
                ) from e

        # 5. Create profile
        profile = UserProfile(
            user_id=user_id,
            first_name=data.first_name.lower(),
            last_name=data.last_name.lower(),
            gender=data.gender,
            date_of_birth=data.date_of_birth,
            info=data.info,
            avatar=file_name,
        )

        try:
            self.users.add(profile)
            await self.users.commit()
            await self.users.refresh(profile)
            log.info(f"Profile created | user_id={user_id}")
        except IntegrityError as e:
            log.error(f"Failed to create profile | user_id={user_id}")
            await self.users.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error creating profile.",
            ) from e

        return profile, avatar_url

    async def get_my_profile(
        self, user_id: int
    ) -> tuple[UserProfile, str | None]:
        """Retrieves a user's profile by their ID.

        :param user_id: The ID of the user whose profile to retrieve.
        :return: The user's profile, or None if no profile is found.
        """
        log.info(f"Fetching profile | user_id={user_id}")
        user = await self.users.get_by_id_with_profile(user_id)

        if not user or not user.is_active:
            log.warning(f"User not found or inactive | user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or inactive.",
            )

        if not user.profile:
            log.warning(f"Profile not created yet | user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not created yet.",
            )

        avatar_url = None
        if user.profile.avatar:
            try:
                avatar_url = await self.s3_client.get_file_url(
                    user.profile.avatar
                )
            except (S3ConnectionError, S3FileUploadError):
                avatar_url = None

        return user.profile, avatar_url

    async def update_my_profile(
        self, user_id: int, data: ProfileUpdateSchema
    ) -> tuple[UserProfile, str | None]:
        """Updates a user's profile.

        :param user_id: The ID of the user whose profile to update.
        :param data: The profile update data.
        :return: A tuple containing the updated UserProfile and the avatar
            URL (if uploaded).
        """
        log.info(f"Updating profile | user_id={user_id}")

        # 1. Load user with profile
        user = await self.users.get_by_id_with_profile(user_id)

        if not user or not user.is_active:
            log.warning(f"User not found or inactive | user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or inactive.",
            )

        if not user.profile:
            log.warning(f"Profile not created yet | user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not created yet.",
            )

        profile = user.profile

        # 3. Update fields
        if data.first_name is not None:
            profile.first_name = data.first_name.lower()

        if data.last_name is not None:
            profile.last_name = data.last_name.lower()

        if data.gender is not None:
            profile.gender = data.gender

        if data.date_of_birth is not None:
            profile.date_of_birth = data.date_of_birth

        if data.info is not None:
            profile.info = data.info

        # 4. Handle avatar replacement
        avatar_url = None

        if data.avatar:
            contents = await data.avatar.read()
            ext = data.avatar.content_type.split("/")[-1].lower()
            ext = "jpg" if ext in ["jpeg", "jpg"] else "png"

            file_name = f"avatars/{user_id}_avatar.{ext}"

            # Delete old avatar if exists
            if profile.avatar:
                try:
                    await self.s3_client.delete_file(profile.avatar)
                    log.info(f"Avatar deleted | user_id={user_id}")
                except S3ConnectionError:
                    log.warning(
                        f"Failed to connect to S3 while deleting avatar: "
                        f"{profile.avatar}"
                    )
                except S3FileUploadError:
                    log.warning(
                        f"Failed to delete avatar from S3: {profile.avatar}"
                    )

            try:
                await self.s3_client.upload_file(
                    file_name, contents, content_type="image/jpeg"
                )
                avatar_url = await self.s3_client.get_file_url(file_name)
                log.info(f"Avatar uploaded | user_id={user_id}")
            except (S3ConnectionError, S3FileUploadError) as e:
                log.error(
                    f"Failed to upload avatar | user_id={user_id} | error={e}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to upload avatar.",
                ) from e

            profile.avatar = file_name

        # 5. Save changes
        try:
            await self.users.commit()
            await self.users.refresh(profile)
            log.info(f"Profile updated | user_id={user_id}")
        except IntegrityError as e:
            log.error(
                f"Error updating profile | user_id={user_id} | error={e}"
            )
            await self.users.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error updating profile.",
            ) from e

        return profile, avatar_url

    async def delete_my_profile(self, user_id: int) -> None:
        """Deletes a user's profile.

        :param user_id: The ID of the user whose profile to delete.
        :return: None
        """
        log.info(f"Deleting profile | user_id={user_id}")

        # 1. Load user with profile
        user = await self.users.get_by_id_with_profile(user_id)

        if not user or not user.is_active:
            log.warning(f"User not found or inactive | user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or inactive.",
            )

        if not user.profile:
            log.warning(f"Profile not created yet | user_id={user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not created yet.",
            )

        profile = user.profile

        # 3. Delete avatar from S3
        try:
            if profile.avatar:
                await self.s3_client.delete_file(profile.avatar)
        except S3ConnectionError:
            log.warning(
                f"Failed to connect to S3 while deleting avatar: "
                f"{profile.avatar}"
            )
        except S3FileUploadError as e:
            log.warning(
                f"Failed deleting avatar from S3: {profile.avatar} | error={e}"
            )

        # 4. Delete profile (SQLAlchemy cascade handles it)
        try:
            await self.users.delete(profile)
            await self.users.commit()
            log.info(f"Profile deleted | user_id={user_id}")
        except IntegrityError as e:
            log.error(
                f"Error deleting profile | user_id={user_id} | error={e}"
            )
            await self.users.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error deleting profile.",
            ) from e
