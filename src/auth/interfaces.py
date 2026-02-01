from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Optional


class JWTAuthManagerInterface(ABC):
    """
    Interface for JWT Authentication Manager.
    Defines methods for creating, decoding, and verifying JWT tokens.
    """

    @abstractmethod
    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new access token.
        """
        pass

    @abstractmethod
    def create_refresh_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new refresh token.
        """
        pass

    @abstractmethod
    def decode_access_token(self, token: str) -> Optional[dict]:
        """
        Decode and validate an access token.
        """
        pass

    @abstractmethod
    def decode_refresh_token(self, token: str) -> dict:
        """
        Decode and validate a refresh token.
        """
        pass

    @abstractmethod
    def verify_refresh_token_or_raise(self, token: str) -> None:
        """
        Verify a refresh token or raise an error if invalid.
        """
        pass

    @abstractmethod
    def verify_access_token_or_raise(self, token: str) -> None:
        """
        Verify an access token or raise an error if invalid.
        """
        pass


class EmailSenderInterface(ABC):

    @abstractmethod
    async def send_activation_email(
        self,
        email: str,
        activation_link: str
    ) -> None:
        """
        Asynchronously send an account activation email.

        Args:
            email (str): The recipient's email address.
            activation_link (str): The activation link to include in the email.
        """
        pass

    # @abstractmethod
    # async def send_activation_complete_email(
    #     self,
    #     email: str,
    #     login_link: str
    # ) -> None:
    #     """
    #     Asynchronously send an email confirming that the account
    #     has been activated.

    #     Args:
    #         email (str): The recipient's email address.
    #         login_link (str): The login link to include in the email.
    #     """
    #     pass

    # @abstractmethod
    # async def send_password_reset_email(
    #     self,
    #     email: str,
    #     reset_link: str
    # ) -> None:
    #     """
    #     Asynchronously send a password reset request email.

    #     Args:
    #         email (str): The recipient's email address.
    #         reset_link (str): The password reset link to include in the email.
    #     """
    #     pass

    # @abstractmethod
    # async def send_password_reset_complete_email(
    #     self,
    #     email: str,
    #     login_link: str
    # ) -> None:
    #     """
    #     Asynchronously send an email confirming that the password
    #     has been reset.

    #     Args:
    #         email (str): The recipient's email address.
    #         login_link (str): The login link to include in the email.
    #     """
    #     pass
