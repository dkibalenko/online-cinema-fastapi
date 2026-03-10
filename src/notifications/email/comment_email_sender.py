from logger_config import get_logger
from notifications.email.base_renderer import TemplateRenderer
from notifications.email.smtp_client import SMTPClient
from notifications.interfaces import CommentEmailSenderInterface

log = get_logger()


class CommentEmailSender(CommentEmailSenderInterface):
    """Class responsible for sending comment-related emails.

    Handles tasks such as sending notifications when someone replies to a
    user's comment.
    """
    def __init__(
        self,
        smtp: SMTPClient,
        renderer: TemplateRenderer,
        template_name: str
    ):
        self.smtp = smtp
        self.renderer = renderer
        self.template_name = template_name

    async def send_comment_reply_email(
        self,
        email: str,
        movie_title: str,
        reply_content: str
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
        log.debug(f"Rendering template '{self.template_name}' for {email}")

        template = self.renderer.get(self.template_name)
        html = template.render(
            movie_title=movie_title, reply_content=reply_content
        )

        log.debug(
            f"Rendered template ({len(html)} chars) for {email}"
        )

        await self.smtp.send(
            email, f"New reply to your comment on {movie_title}", html
        )
