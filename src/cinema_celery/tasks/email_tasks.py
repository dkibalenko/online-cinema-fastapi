import asyncio

from config import get_settings
from cinema_celery.celery_app import app
from auth.email_manager import EmailSender


def get_email_sender() -> EmailSender:
    settings = get_settings()
    return EmailSender(
        hostname=settings.SMTP_SERVER,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        use_tls=settings.SMTP_USE_TLS,
        template_dir=settings.PATH_TO_EMAIL_TEMPLATES_DIR,
        activation_email_template_name=settings.ACTIVATION_EMAIL_TEMPLATE_NAME,
        activation_complete_email_template_name=settings.ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME,
        password_email_template_name=settings.PASSWORD_RESET_TEMPLATE_NAME,
        password_complete_email_template_name=settings.PASSWORD_RESET_COMPLETE_TEMPLATE_NAME,
    )


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
