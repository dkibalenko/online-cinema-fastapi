from datetime import date

from pydantic import BaseModel, ConfigDict

from users.enums import GenderEnum, UserGroupEnum


class UpdateGroupSchema(BaseModel):
    group: UserGroupEnum


class UserAdminResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    group: UserGroupEnum

    model_config = ConfigDict(from_attributes=True)


class UserFilterParams(BaseModel):
    email: str | None = None
    group: UserGroupEnum | None = None
    is_active: bool | None = None


class AdminResetPasswordSchema(BaseModel):
    new_password: str


class AdminUserProfileCreateSchema(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    gender: GenderEnum | None = None
    birth_date: date | None = None
    info: str | None = None
    avatar_url: str | None = None  # Admin can set URL directly


class AdminUserProfileUpdateSchema(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    gender: GenderEnum | None = None
    birth_date: date | None = None
    info: str | None = None
    avatar_url: str | None = None


class AdminUserProfileResponse(BaseModel):
    id: int
    user_id: int
    first_name: str | None
    last_name: str | None
    gender: GenderEnum | None
    birth_date: date | None
    info: str | None
    avatar_url: str | None

    model_config = ConfigDict(from_attributes=True)
