from datetime import date
from typing import Annotated, Optional

from fastapi import UploadFile, Form, File
from fastapi.exceptions import RequestValidationError
from pydantic import (
    BaseModel,
    field_validator,
    AfterValidator,
    ConfigDict,
    ValidationError
)

from users.validators import (
    validate_name,
    validate_birth_date,
    validate_gender,
    validate_image
)


class ProfileBaseSchema(BaseModel):
    first_name: Annotated[str, AfterValidator(validate_name)]
    last_name: Annotated[str, AfterValidator(validate_name)]
    gender: Annotated[str, AfterValidator(validate_gender)]
    date_of_birth: Annotated[date, AfterValidator(validate_birth_date)]
    info: str

    @field_validator("info", mode="after")
    @classmethod
    def validate_info(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                "Info field cannot be empty or contain only spaces."
            )
        return value


class ProfileCreationSchema(ProfileBaseSchema):
    avatar: Annotated[Optional[UploadFile], AfterValidator(validate_image)] = None

    @classmethod
    def as_form(
        cls,
        first_name: Annotated[str, Form(...)],
        last_name: Annotated[str, Form(...)],
        gender: Annotated[str, Form(...)],
        date_of_birth: Annotated[date, Form(...)],
        info: Annotated[str, Form(...)],
        avatar: UploadFile | None = File(None),  # stream the file efficiently, validate file type, support multipart/form‑data, avoid loading large files into memory
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
    user_id: int
    avatar: str | None

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdateSchema(BaseModel):
    first_name: Annotated[Optional[str], AfterValidator(validate_name)] = None
    last_name: Annotated[Optional[str], AfterValidator(validate_name)] = None
    gender: Annotated[Optional[str], AfterValidator(validate_gender)] = None
    date_of_birth: Annotated[Optional[date], AfterValidator(validate_birth_date)] = None
    info: Optional[str] = None
    avatar: Annotated[Optional[UploadFile], AfterValidator(validate_image)] = None

    @field_validator("info", mode="after")
    @classmethod
    def validate_info(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("Info field cannot be empty or contain only spaces.")
        return value

    @classmethod
    def as_form(
        cls,
        first_name: Annotated[Optional[str], Form()] = None,
        last_name: Annotated[Optional[str], Form()] = None,
        gender: Annotated[Optional[str], Form()] = None,
        date_of_birth: Annotated[Optional[date], Form()] = None,
        info: Annotated[Optional[str], Form()] = None,
        avatar: UploadFile | None = File(None),
    ) -> "ProfileUpdateSchema":
        try:
            return cls(
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                date_of_birth=date_of_birth,
                info=info,
                avatar=avatar,
            )
        except ValidationError as e:
            raise RequestValidationError(e.errors())
