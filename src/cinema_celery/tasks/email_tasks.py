import asyncio

from config import get_settings
from cinema_celery.celery_app import app
from notifications.factories import create_auth_email_sender
from notifications.interfaces import EmailSenderInterface


def get_email_sender() -> EmailSenderInterface:
    settings = get_settings()
    return create_auth_email_sender(settings)


@app.task
def send_activation_email(email: str, token: str):
    sender = get_email_sender()
    asyncio.run(sender.send_activation_email(email, token))


@app.task
def send_activation_complete_email(email: str, login_link: str):
    sender = get_email_sender()
    asyncio.run(sender.send_activation_complete_email(email, login_link))


@app.task
def send_password_reset_email(email: str, token: str):
    sender = get_email_sender()
    asyncio.run(sender.send_password_reset_email(email, token))


@app.task
def send_password_reset_complete_email(email: str, login_link: str):
    sender = get_email_sender()
    asyncio.run(sender.send_password_reset_complete_email(email, login_link))
