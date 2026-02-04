from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import SecretStr


class BaseAppSettings(BaseSettings):
    # Pydantic load .env automatically
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    BASE_DIR: Path = Path(__file__).parent

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

    # Safe defaults
    PATH_TO_EMAIL_TEMPLATES_DIR: str = str(BASE_DIR / "auth" / "templates")
    ACTIVATION_EMAIL_TEMPLATE_NAME: str = "activation_request.html"
    ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME: str = "activation_complete.html"
    PASSWORD_RESET_TEMPLATE_NAME: str = "password_reset_request.html"
    PASSWORD_RESET_COMPLETE_TEMPLATE_NAME: str = "password_reset_complete.html"

    LOGIN_TIME_DAYS: int = 7


class Settings(BaseAppSettings):
    # Optional defaults — Pydantic will override from .env if present
    POSTGRES_USER: str = "cinema_user"
    POSTGRES_PASSWORD: str = "cinema_password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_DB_PORT: int = 5432
    POSTGRES_DB: str = "cinema_db"

    JWT_SECRET_KEY_ACCESS: SecretStr
    JWT_SECRET_KEY_REFRESH: SecretStr
    JWT_SIGNING_ALGORITHM: str


def get_settings() -> BaseAppSettings:
    return Settings()
