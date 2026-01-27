# src/auth/utils.py
import secrets
from passlib.context import CryptContext


pwd_context = CryptContext(
    schemes=["bcrypt"],  # primary hashing algorithm, which is cryptographically secure for password storage
    bcrypt__rounds=14,  # number of iterations (rounds) bcrypt performs when hashing a password
    deprecated="auto"  # Automatically detects and handles legacy hashed passwords from older schemes during verification
)


def hash_password(password: str) -> str:
    """
    Hash a password using the configured CryptContext.

    Args:
        password (str): The password to hash.

    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify that a given plain password matches a given hashed password.

    Args:
        plain_password (str): The plain password to verify.
        hashed_password (str): The hashed password to verify against.

    Returns:
        bool: True if the plain password matches the hashed password, 
        False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)



def generate_secure_token(length: int = 32) -> str:
    """
    Generate a secure random token.

    Returns:
        str: Securely generated token.
    """
    return secrets.token_urlsafe(length)
