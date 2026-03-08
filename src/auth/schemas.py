from pydantic import BaseModel, EmailStr, Field, field_validator

from users.validators import validate_password_complexity


class MessageResponseSchema(BaseModel):
    message: str


class BaseEmailPasswordSchema(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        """Validate an email address.

        The given email is converted to lowercase to ensure consistency.

        :param value: The email address to validate.
        :return: The validated email address.
        :raises ValueError: If the email address is not valid.
        """
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        """Validate a password against complexity rules.

        The password must contain at least 8 characters, one uppercase letter,
        one lowercase letter, one digit, and one special character.

        :param value: The password to validate.
        :return: The validated password.
        :raises ValueError: If the password does not meet the complexity rules.
        """
        return validate_password_complexity(value)


class UserRegistrationRequestSchema(BaseEmailPasswordSchema):
    pass


class UserRegistrationResponseSchema(BaseModel):
    id: int
    email: EmailStr

    model_config = {"from_attributes": True}


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
        """Validates the given new password against password complexity rules.

        Args:
            value (str): The new password to validate.

        Returns:
            str: The validated password.

        Raises:
            ValueError: If the password does not meet the complexity rules.
        """
        return validate_password_complexity(value)
