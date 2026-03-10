import asyncio

from cinema_celery.celery_app import app
from config import get_settings
from notifications.factories import create_auth_email_sender
from notifications.interfaces import AuthEmailSenderInterface


def get_email_sender() -> AuthEmailSenderInterface:
    """Returns an instance of AuthEmailSenderInterface.

    This function is used to send email notifications for
    authentication-related events.

    :return: An instance of AuthEmailSenderInterface.
    """
    settings = get_settings()
    return create_auth_email_sender(settings)


@app.task
def send_activation_email(email: str, token: str):
    """Asynchronously sends an email confirming the account has been created.

    Args:
        email (str): The recipient's email address.
        token (str): The activation token to include in the email.
    """
    sender = get_email_sender()
    asyncio.run(sender.send_activation_email(email, token))


@app.task
def send_activation_complete_email(email: str, login_link: str):
    """Asynchronously sends an email confirming the account has been activated.

    Args:
        email (str): The recipient's email address.
        login_link (str): The login link to include in the email.
    """
    sender = get_email_sender()
    asyncio.run(sender.send_activation_complete_email(email, login_link))


@app.task
def send_password_reset_email(email: str, token: str):
    """Asynchronously sends an email with a password reset link.

    Args:
        email (str): The recipient's email address.
        token (str): The password reset token to include in the email.
    """
    sender = get_email_sender()
    asyncio.run(sender.send_password_reset_email(email, token))


@app.task
def send_password_reset_complete_email(email: str, login_link: str):
    """Asynchronously sends an email confirming the password has been reset.

    Args:
        email (str): The recipient's email address.
        login_link (str): The login link to include in the email.
    """
    sender = get_email_sender()
    asyncio.run(sender.send_password_reset_complete_email(email, login_link))
