import asyncio

from cinema_celery.celery_app import app
from config import get_settings
from notifications.factories import create_comment_email_sender
from notifications.interfaces import CommentEmailSenderInterface


def get_email_sender() -> CommentEmailSenderInterface:
    """Returns an instance of CommentEmailSenderInterface.

    This function is used to send email notifications when a new reply
    is posted.

    :return: An instance of CommentEmailSenderInterface.
    """
    settings = get_settings()
    return create_comment_email_sender(settings)


@app.task
def send_comment_reply_notification(
    email: str, movie_title: str, reply_content: str
):
    """Asynchronously sends an email notification when a new reply is posted.

    Args:
        email (str): The recipient's email address.
        movie_title (str): The title of the movie the comment was
            posted on.
        reply_content (str): The content of the reply to the comment.
    """
    sender = get_email_sender()
    asyncio.run(
        sender.send_comment_reply_email(
            email=email,
            movie_title=movie_title,
            reply_content=reply_content,
        )
    )
