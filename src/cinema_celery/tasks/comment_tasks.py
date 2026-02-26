import asyncio

from config import get_settings
from cinema_celery.celery_app import app
from notifications.factories import create_comment_email_sender
from notifications.interfaces import EmailSenderInterface


def get_email_sender() -> EmailSenderInterface:
    settings = get_settings()
    return create_comment_email_sender(settings)


@app.task
def send_comment_reply_notification(
    email: str,
    movie_title: str,
    reply_content: str
):
    sender = get_email_sender()
    asyncio.run(
        sender.send_custom_email(
            email=email,
            subject=f"New reply to your comment on {movie_title}",
            template_name=sender.comment_reply_template,
            context={"movie_title": movie_title, "reply_content": reply_content}
        )
    )
