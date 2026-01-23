import re

from email_validator import validate_email, EmailNotValidError


def validate_password_complexity(password: str) -> str:
    """
    Validates the complexity of a given password.

    Checks that the password contains at least 8 characters,
    one uppercase letter, one lower letter, one digit, and one 
    special character.

    Raises a ValueError with a descriptive message if the password does not
    meet the complexity requirements.

    Returns the validated password.
    """
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")
    if not re.search(r'[A-Z]', password):
        raise ValueError("Password must contain at least one uppercase letter.")
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
    Validates a given email address.

    Tries to validate the given email address using the email_validator package.
    If the email address is invalid, raises a ValueError with a descriptive message.
    If the email address is valid, returns the normalized email address.

    :raises ValueError: If the email address is invalid.
    :return str: The validated and normalized email address.
    """
    try:
        email_info = validate_email(user_email, check_deliverability=False)
        email = email_info.normalized
    except EmailNotValidError as error:
        raise ValueError(str(error))
    else:
        return email
