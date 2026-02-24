from fastapi import Depends

from config import get_settings, BaseAppSettings
from notifications.factories import create_auth_email_sender


def get_auth_email_sender(settings: BaseAppSettings = Depends(get_settings)):
    return create_auth_email_sender(settings)
