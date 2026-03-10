from typing import Annotated

from fastapi import Depends

from config import BaseAppSettings, get_settings
from notifications.factories import create_auth_email_sender
from notifications.interfaces import AuthEmailSenderInterface


def get_auth_email_sender(
    settings: Annotated[BaseAppSettings, Depends(get_settings)],
) -> AuthEmailSenderInterface:
    """Returns an instance of AuthEmailSenderInterface.

    This function is used to send email notifications for
    authentication-related events.

    :param settings: An instance of BaseAppSettings.
    :return: An instance of AuthEmailSenderInterface.
    """
    return create_auth_email_sender(settings)
