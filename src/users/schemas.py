from datetime import date
from typing import Annotated

from fastapi import File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
)

from users.validators import (
    validate_birth_date,
    validate_gender,
    validate_image,
    validate_name,
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
        """Validates the info field.

        This method checks if the info field is provided by ensuring it is not
        empty or contain only spaces.

        :raises ValueError: If the info field is empty or contains only spaces.
        :return: The validated info field.
        """
        if not value.strip():
            raise ValueError(
                "Info field cannot be empty or contain only spaces."
            )
        return value


class ProfileCreationSchema(ProfileBaseSchema):
    avatar: Annotated[UploadFile | None, AfterValidator(validate_image)] = None

    @classmethod
    def as_form(
        cls,
        first_name: Annotated[str, Form(...)],
        last_name: Annotated[str, Form(...)],
        gender: Annotated[str, Form(...)],
        date_of_birth: Annotated[date, Form(...)],
        info: Annotated[str, Form(...)],
        # stream the file efficiently, validate file type,
        # support multipart/form‑data, avoid loading large files into memory
        avatar: Annotated[UploadFile | None, File()] = None,
    ) -> "ProfileCreationSchema":
        """Defines how to map form data to the Pydantic schema.

        :param first_name: The user's first name.
        :param last_name: The user's last name.
        :param gender: The user's gender.
        :param date_of_birth: The user's date of birth.
        :param info: The user's bio information.
        :param avatar: The user's avatar image.
        :return: An instance of ProfileCreationSchema.
        :raises RequestValidationError: If the provided data is invalid.
        """
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
            raise RequestValidationError(e.errors()) from e


class ProfileResponseSchema(ProfileBaseSchema):
    id: int
    user_id: int
    avatar: str | None

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdateSchema(BaseModel):
    first_name: Annotated[str | None, AfterValidator(validate_name)] = None
    last_name: Annotated[str | None, AfterValidator(validate_name)] = None
    gender: Annotated[str | None, AfterValidator(validate_gender)] = None
    date_of_birth: Annotated[
        date | None, AfterValidator(validate_birth_date)
    ] = None
    info: str | None = None
    avatar: Annotated[UploadFile | None, AfterValidator(validate_image)] = None

    @field_validator("info", mode="after")
    @classmethod
    def validate_info(cls, value: str | None) -> str | None:
        """Validates the info field.

        This method checks if the info field is provided by ensuring it is not
        empty or contain only spaces.

        :raises ValueError: If the info field is empty or contains only spaces.
        :return: The validated info field.
        """
        if value is not None and not value.strip():
            raise ValueError(
                "Info field cannot be empty or contain only spaces."
            )
        return value

    @classmethod
    def as_form(
        cls,
        first_name: Annotated[str | None, Form()] = None,
        last_name: Annotated[str | None, Form()] = None,
        gender: Annotated[str | None, Form()] = None,
        date_of_birth: Annotated[date | None, Form()] = None,
        info: Annotated[str | None, Form()] = None,
        avatar: Annotated[UploadFile | None, File()] = None,
    ) -> "ProfileUpdateSchema":
        """Defines how to map form data to the Pydantic schema.

        :param first_name: The user's first name.
        :param last_name: The user's last name.
        :param gender: The user's gender.
        :param date_of_birth: The user's date of birth.
        :param info: The user's bio information.
        :param avatar: The user's avatar image.
        :return: An instance of ProfileUpdateSchema.
        :raises RequestValidationError: If the provided data is invalid.
        """
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
            raise RequestValidationError(e.errors()) from e
