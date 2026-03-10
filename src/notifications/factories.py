from config import BaseAppSettings
from notifications.email.auth_email_sender import AuthEmailSender
from notifications.email.base_renderer import TemplateRenderer
from notifications.email.comment_email_sender import CommentEmailSender
from notifications.email.smtp_client import SMTPClient


def create_auth_email_sender(settings: BaseAppSettings):
    """Returns an instance of AuthEmailSender.

    This function is used to send email notifications for
    authentication-related events.

    :param settings: An instance of BaseAppSettings.
    :return: An instance of AuthEmailSender.
    """
    smtp = SMTPClient(
        hostname=settings.SMTP_SERVER,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        use_tls=settings.SMTP_USE_TLS,
        from_email=settings.SMTP_USERNAME,
    )
    renderer = TemplateRenderer(settings.PATH_TO_AUTH_EMAIL_TEMPLATES_DIR)

    return AuthEmailSender(
        smtp=smtp,
        renderer=renderer,
        activation_template=settings.ACTIVATION_EMAIL_TEMPLATE_NAME,
        activation_complete_template=(
            settings.ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME
        ),
        password_reset_template=settings.PASSWORD_RESET_TEMPLATE_NAME,
        password_reset_complete_template=(
            settings.PASSWORD_RESET_COMPLETE_TEMPLATE_NAME
        ),
    )


def create_comment_email_sender(settings: BaseAppSettings):
    """Returns an instance of CommentEmailSender.

    This function is used to send email notifications when a new reply
    is posted.

    :param settings: An instance of BaseAppSettings.
    :return: An instance of CommentEmailSender.
    """
    smtp = SMTPClient(
        hostname=settings.SMTP_SERVER,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        use_tls=settings.SMTP_USE_TLS,
        from_email=settings.SMTP_USERNAME,
    )
    renderer = TemplateRenderer(
        settings.PATH_TO_CELERY_TASKS_EMAIL_TEMPLATES_DIR
    )

    return CommentEmailSender(
        smtp=smtp,
        renderer=renderer,
        template_name=settings.COMMENT_REPLY_TEMPLATE_NAME,
    )
