# mypy: ignore-errors

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class BaseAppSettings(BaseSettings):
    # Pydantic load .env automatically
    model_config = {
        "env_file": BASE_DIR / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    BASE_DIR: Path = Path(__file__).parent
    BASE_URL: str = "http://localhost:8000"

    # Safe defaults
    CERT_JSON_PATH: str = str(
        BASE_DIR / "seeding" / "seed_data" / "certifications.json"
    )
    MOVIE_JSON_PATH: str = str(
        BASE_DIR / "seeding" / "seed_data" / "movies.json"
    )
    GENRE_JSON_PATH: str = str(
        BASE_DIR / "seeding" / "seed_data" / "genres.json"
    )
    STARS_JSON_PATH: str = str(
        BASE_DIR / "seeding" / "seed_data" / "stars.json"
    )
    DIRECTORS_JSON_PATH: str = str(
        BASE_DIR / "seeding" / "seed_data" / "directors.json"
    )

    # Required sensitive values - Pydantic will override from .env
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_USE_TLS: bool
    MAILHOG_API_PORT: int

    S3_STORAGE_HOST: str
    S3_STORAGE_PORT: int
    S3_STORAGE_ACCESS_KEY: str
    S3_STORAGE_SECRET_KEY: str
    S3_BUCKET_NAME: str
    S3_PUBLIC_HOST: str = "localhost"  # browser-reachable host for redirect URLs

    # Safe defaults
    PATH_TO_AUTH_EMAIL_TEMPLATES_DIR: str = str(
        BASE_DIR / "auth" / "templates"
    )
    PATH_TO_CELERY_TASKS_EMAIL_TEMPLATES_DIR: str = str(
        BASE_DIR / "cinema_celery" / "tasks" / "templates"
    )
    ACTIVATION_EMAIL_TEMPLATE_NAME: str = "activation_request.html"
    ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME: str = "activation_complete.html"
    PASSWORD_RESET_TEMPLATE_NAME: str = "password_reset_request.html"
    PASSWORD_RESET_COMPLETE_TEMPLATE_NAME: str = "password_reset_complete.html"
    COMMENT_REPLY_TEMPLATE_NAME: str = "comment_reply.html"

    LOGIN_TIME_DAYS: int = 7

    @property
    def S3_STORAGE_ENDPOINT(self) -> str:
        """Get the S3-compatible storage endpoint URL.

        Returns:
            str: The S3-compatible storage endpoint URL in the format
                "http://host:port".
        """
        return f"http://{self.S3_STORAGE_HOST}:{self.S3_STORAGE_PORT}"

    @property
    def S3_PUBLIC_ENDPOINT(self) -> str:
        """Browser-reachable MinIO URL used in redirect responses.

        S3_STORAGE_HOST is the internal Docker hostname (minio), which
        browsers cannot resolve. S3_PUBLIC_HOST is the externally accessible
        host (localhost in dev, CDN/domain in prod).

        Returns:
            str: Public-facing MinIO endpoint URL.
        """
        return f"http://{self.S3_PUBLIC_HOST}:{self.S3_STORAGE_PORT}"


class Settings(BaseAppSettings):
    # Optional defaults — Pydantic will override from .env if present
    POSTGRES_USER: str = "cinema_user"
    POSTGRES_PASSWORD: str = "cinema_password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_DB_PORT: int = 5432
    POSTGRES_DB: str = "cinema_db"
    SQL_ECHO: bool = False

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    CACHE_REDIS_URL: str

    JWT_SECRET_KEY_ACCESS: SecretStr
    JWT_SECRET_KEY_REFRESH: SecretStr
    JWT_SIGNING_ALGORITHM: str


def get_settings() -> BaseAppSettings:
    """Retrieve the application settings.

    This function returns an instance of the Settings class, which contains
    the application settings.

    Returns:
        BaseAppSettings: An instance of the Settings class.
    """
    return Settings()  # type: ignore[call-arg]
