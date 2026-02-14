from typing import Tuple

from fastapi import status, HTTPException
from sqlalchemy.exc import IntegrityError

from exceptions import InvalidTokenError, TokenExpiredError
from users.models import UserProfile
from users.repository import UserRepository
from users.schemas import ProfileCreationSchema
from auth.interfaces import JWTAuthManagerInterface
from storages.exceptions import S3ConnectionError, S3FileUploadError
from storages.interfaces import S3StorageInterface
from logger_config import get_logger


log = get_logger()


class UserService:
    def __init__(
        self,
        users: UserRepository,
        jwt: JWTAuthManagerInterface,
        s3_client: S3StorageInterface
    ):
        self.users = users
        self.jwt = jwt
        self.s3_client = s3_client

    async def create_user_profile(
        self,
        user_id: int,
        data: ProfileCreationSchema,
        jwt_token: str
    ) -> Tuple[UserProfile, str | None]:
        # 1. Validate token
        try:
            self.jwt.verify_access_token_or_raise(jwt_token)
        except TokenExpiredError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired."
            )
        except InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token."
            )

        jwt_payload = self.jwt.decode_access_token(jwt_token)

        try:
            current_user_id = int(jwt_payload.get("user_id"))
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload."
            )

        # 2. Load current user with group
        current_user = await self.users.get_by_id_with_group(current_user_id)

        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found."
            )

        # 3. Load target user
        target_user = await self.users.get_by_id_with_profile(user_id)

        if not target_user or not target_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive."
            )

        # 4. Check permissions
        if (
            not current_user_id == user_id
            and not current_user.has_group(UserGroupEnum.ADMIN)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this profile."
            )

        # 5. Check if profile already exists
        if target_user.profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile already exists."
            )

        # 6. Upload avatar (optional)
        avatar_url = None
        file_name = None

        if data.avatar:
            contents = await data.avatar.read()

            ext = data.avatar.content_type.split("/")[-1].lower()
            ext = "jpg" if ext in ["jpeg", "jpg"] else "png"

            file_name = f"avatars/{user_id}_avatar.{ext}"

            try:
                await self.s3_client.upload_file(file_name, contents)
                avatar_url = await self.s3_client.get_file_url(file_name)
            except (S3ConnectionError, S3FileUploadError):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to upload avatar. Please try again later."
                )

        # 7. Create profile
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
        except IntegrityError:
            await self.users.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error creating profile."
            )

        return profile, avatar_url

    async def get_my_profile(self, user_id: int) -> Tuple[UserProfile, str | None]:
        user = await self.users.get_by_id_with_profile(user_id)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or inactive."
            )

        if not user.profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not created yet."
            )

        avatar_url = None
        if user.profile.avatar:
            try:
                avatar_url = await self.s3_client.get_file_url(user.profile.avatar)
            except (S3ConnectionError, S3FileUploadError):
                avatar_url = None

        return user.profile, avatar_url
