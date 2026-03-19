from config import BaseAppSettings
from pydantic import SecretStr


class TestSettings(BaseAppSettings):
    TESTING: bool = True

    POSTGRES_USER: str = "test_user"
    POSTGRES_PASSWORD: str = "test_password"
    POSTGRES_DB: str = "test_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_DB_PORT: int = 5432

    JWT_SECRET_KEY_ACCESS: SecretStr = SecretStr("test_access")
    JWT_SECRET_KEY_REFRESH: SecretStr = SecretStr("test_refresh")
    JWT_SIGNING_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # REQUIRED SMTP FIELDS
    SMTP_SERVER: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USERNAME: str = "test"
    SMTP_PASSWORD: str = "test"
    SMTP_USE_TLS: bool = False
    MAILHOG_API_PORT: int = 8025

    S3_STORAGE_HOST: str = "localhost"
    S3_STORAGE_PORT: int = 9001
    S3_STORAGE_ACCESS_KEY: str = "test"
    S3_STORAGE_SECRET_KEY: str = "test"
    S3_BUCKET_NAME: str = "test-bucket"

    CELERY_BROKER_URL: str = "redis://localhost:6380/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6380/1"


def get_test_settings():
    """Retrieves an instance of the TestSettings class.

    The TestSettings class is a subclass of BaseAppSettings, containing
    the application settings used for testing.

    Returns:
        TestSettings: An instance of the TestSettings class.
    """
    return TestSettings()
