from abc import ABC, abstractmethod

from fastapi import WebSocket


class AuthEmailSenderInterface(ABC):
    @abstractmethod
    async def send_activation_email(
        self, email: str, activation_link: str
    ) -> None:
        """Asynchronously send an account activation email.

        Args:
            email (str): The recipient's email address.
            activation_link (str): The activation link to include in the email.
        """
        pass

    @abstractmethod
    async def send_activation_complete_email(
        self, email: str, login_link: str
    ) -> None:
        """Asynchronously send email confirming the account has been activated.

        Args:
            email (str): The recipient's email address.
            login_link (str): The login link to include in the email.
        """
        pass

    @abstractmethod
    async def send_password_reset_email(
        self, email: str, reset_link: str
    ) -> None:
        """Asynchronously send a password reset request email.

        Args:
            email (str): The recipient's email address.
            reset_link (str): The password reset link to include in the email.
        """
        pass

    @abstractmethod
    async def send_password_reset_complete_email(
        self, email: str, login_link: str
    ) -> None:
        """Asynchronously send an email confirming the password has been reset.

        Args:
            email (str): The recipient's email address.
            login_link (str): The login link to include in the email.
        """
        pass


class CommentEmailSenderInterface(ABC):
    @abstractmethod
    async def send_comment_reply_email(
        self, email: str, movie_title: str, reply_content: str
    ) -> None:
        """Asynchronously send an email when someone replies to their comment.

        The email will contain the title of the movie and the content of the
        reply.

        Args:
            email (str): The recipient's email address.
            movie_title (str): The title of the movie the comment was
                posted on.
            reply_content (str): The content of the reply to the comment.
        """
        pass


class WebSocketConnectionManagerInterface(ABC):
    @abstractmethod
    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        """Asynchronously connect a user to a WebSocket.

        Args:
            user_id (int): The user's ID.
            websocket (WebSocket): The WebSocket connection.
        """
        pass

    @abstractmethod
    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        """Disconnect a user from a WebSocket.

        Args:
            user_id (int): The user's ID.
            websocket (WebSocket): The WebSocket connection.
        """
        pass

    @abstractmethod
    async def send_to_user(self, user_id: int, message: dict) -> None:
        """Asynchronously send a message to a user.

        Args:
            user_id (int): The user's ID.
            message (dict): The message to send.
        """
        pass
