import re
from datetime import date
from io import BytesIO

from fastapi import UploadFile
from PIL import Image
import email_validator

from auth.enums import GenderEnum


def validate_password_complexity(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")
    if not re.search(r'[A-Z]', password):
        raise ValueError(
            "Password must contain at least one uppercase letter."
        )
    if not re.search(r'[a-z]', password):
        raise ValueError("Password must contain at least one lower letter.")
    if not re.search(r'\d', password):
        raise ValueError("Password must contain at least one digit.")
    if not re.search(r'[@$!%*?&#]', password):
        raise ValueError(
            "Password must contain at least one special character: "
            "@, $, !, %, *, ?, #, &."
        )
    return password


def validate_email(user_email: str) -> str:
    """
    Validates an email address.

    :param user_email: The email address to validate.
    :return: The validated email address.
    :raises ValueError: If the email address is not valid.
    """
    try:
        email_info = email_validator.validate_email(
            user_email, check_deliverability=False
        )
        email = email_info.normalized
    except email_validator.EmailNotValidError as error:
        raise ValueError(str(error))
    else:
        return email


def validate_name(name: str) -> str:
    """
    Validates a name by checking if it only contains english letters.
    """
    if re.search(r'^[A-Za-z]*$', name) is None:
        raise ValueError(f"{name} contains non-english letters")
    return name


def validate_image(avatar: UploadFile) -> UploadFile:
    """
    Validates an image by checking if it is one of the supported formats
    (JPG, JPEG, PNG) and its size does not exceed 1 MB.

    :param avatar: The image to validate.
    :return: The validated image.
    :raises ValueError: If the image format is not supported or the size
        exceeds 1 MB.
    :raises IOError: If the image format is invalid.
    """
    supported_image_formats = ["JPG", "JPEG", "PNG"]
    max_file_size = 1 * 1024 * 1024

    contents = avatar.file.read()

    if len(contents) > max_file_size:
        raise ValueError("Image size exceeds 1 MB")

    try:
        image = Image.open(BytesIO(contents))
        avatar.file.seek(0)
        image_format = image.format

        if image_format not in supported_image_formats:
            raise ValueError(
                f"Unsupported image format: {image_format}. Use one of next: "
                f"{supported_image_formats}"
            )
    except IOError:
        raise ValueError("Invalid image format")

    return avatar


def validate_gender(gender: str) -> str:
    if gender not in GenderEnum.__members__.values():
        raise ValueError(
            f"Gender must be one of: {', '.join(g.value for g in GenderEnum)}"
        )
    return gender


def validate_birth_date(birth_date: date) -> date:
    """
    Validates a birth date by checking if it is in the past and the user is at
    least 18 years old.

    :param birth_date: The birth date to validate.
    :return: The validated birth date.
    :raises ValueError: If the birth date is in the future or the user is
        less than 18 years old.
    """
    if birth_date.year < 1900:
        raise ValueError(
            "Invalid birth date - year must be greater than 1900."
        )

    age = (date.today() - birth_date).days // 365

    if age < 18:
        raise ValueError("You must be at least 18 years old to register.")

    return birth_date
