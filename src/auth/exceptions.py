# src/auth/exceptions.py
from exceptions import BaseSecurityError


class AuthError(BaseSecurityError):
    pass


class BaseEmailError(Exception):
    """Base class for all exceptions raised by email notification module."""
    pass
