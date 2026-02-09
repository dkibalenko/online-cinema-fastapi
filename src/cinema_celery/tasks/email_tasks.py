import asyncio

from cinema_celery.celery_app import app
from auth.email_manager import EmailSender


@app.task
def send_activation_email(email: str, token: str):
    sender = EmailSender()
    asyncio.run(sender.send_activation_email(email, token))


@app.task
def send_activation_complete_email(email: str, login_link: str):
    sender = EmailSender()
    asyncio.run(sender.send_activation_complete_email(email, login_link))


@app.task
def send_password_reset_email(email: str, token: str):
    sender = EmailSender()
    asyncio.run(sender.send_password_reset_email(email, token))


@app.task
def send_password_reset_complete_email(email: str, login_link: str):
    sender = EmailSender()
    asyncio.run(sender.send_password_reset_complete_email(email, login_link))
