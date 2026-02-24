from config import BaseAppSettings
from notifications.email_manager import EmailSender
from notifications.interfaces import EmailSenderInterface


def create_auth_email_sender(
    settings: BaseAppSettings
) -> EmailSenderInterface:
    """
    Factory function to create an EmailSender for
    authentication-related emails.
    """
    return EmailSender(
        hostname=settings.SMTP_SERVER,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        use_tls=settings.SMTP_USE_TLS,
        template_dir=settings.PATH_TO_AUTH_EMAIL_TEMPLATES_DIR,
        activation_email_template_name=settings.ACTIVATION_EMAIL_TEMPLATE_NAME,
        activation_complete_email_template_name=(
            settings.ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME
        ),
        password_email_template_name=settings.PASSWORD_RESET_TEMPLATE_NAME,
        password_complete_email_template_name=(
            settings.PASSWORD_RESET_COMPLETE_TEMPLATE_NAME
        ),
    )


def create_comment_email_sender(
    settings: BaseAppSettings
) -> EmailSenderInterface:
    """
    Factory function to create an EmailSender for comment-related emails.
    """
    return EmailSender(
        hostname=settings.SMTP_SERVER,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        use_tls=settings.SMTP_USE_TLS,
        template_dir=settings.PATH_TO_CELERY_TASKS_EMAIL_TEMPLATES_DIR,
        comment_reply_template_name=settings.COMMENT_REPLY_TEMPLATE_NAME,
    )
