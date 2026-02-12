from datetime import date
from typing import Annotated, Optional

from fastapi import UploadFile, Form, File
from fastapi.exceptions import RequestValidationError
from pydantic import (
    BaseModel,
    EmailStr,
    field_validator,
    Field,
    AfterValidator,
    ConfigDict,
    ValidationError
)

from auth.validators import (
    validate_password_complexity,
    validate_name,
    validate_birth_date,
    validate_gender,
    validate_image
)


class MessageResponseSchema(BaseModel):
    message: str


class BaseEmailPasswordSchema(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        return validate_password_complexity(value)


class UserRegistrationRequestSchema(BaseEmailPasswordSchema):
    pass


class UserRegistrationResponseSchema(BaseModel):
    id: int
    email: EmailStr

    model_config = {
        "from_attributes": True
    }


class UserActivationRequestSchema(BaseModel):
    email: EmailStr
    token: str = Field(..., description="Activation token")


class ResendActivationRequestSchema(BaseModel):
    email: EmailStr


class UserLoginRequestSchema(BaseEmailPasswordSchema):
    pass


class UserLoginResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequestSchema(BaseModel):
    refresh_token: str


class TokenRefreshResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr


class PasswordResetCompleteRequestSchema(BaseModel):
    token: str
    password: str


class ChangePasswordSchema(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value):
        return validate_password_complexity(value)


class ProfileBaseSchema(BaseModel):
    first_name: Annotated[str, AfterValidator(validate_name)]
    last_name: Annotated[str, AfterValidator(validate_name)]
    gender: Annotated[str, AfterValidator(validate_gender)]
    date_of_birth: Annotated[date, AfterValidator(validate_birth_date)]
    info: str
    user_id: int | None = None

    @field_validator("info", mode="after")
    @classmethod
    def validate_info(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                "Info field cannot be empty or contain only spaces."
            )
        return value


class ProfileCreationSchema(ProfileBaseSchema):
    avatar: Annotated[Optional[UploadFile], AfterValidator(validate_image)]

    @classmethod
    def as_form(
        cls,
        first_name: Annotated[str, Form(...)],
        last_name: Annotated[str, Form(...)],
        gender: Annotated[str, Form(...)],
        date_of_birth: Annotated[date, Form(...)],
        info: Annotated[str, Form(...)],
        avatar: UploadFile | None = File(None),
    ) -> "ProfileCreationSchema":
        """
        A helper class method that defines how to map form data
        to the Pydantic schema.
        """
        try:
            return cls(
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                date_of_birth=date_of_birth,
                info=info,
                avatar=avatar
            )
        except ValidationError as e:
            raise RequestValidationError(e.errors())


class ProfileResponseSchema(ProfileBaseSchema):
    id: int
    avatar: str | None

    model_config = ConfigDict(from_attributes=True)
