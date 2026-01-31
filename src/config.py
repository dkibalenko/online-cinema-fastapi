# src/config.py
import os
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import SecretStr


class BaseAppSettings(BaseSettings):
    # Pydantic load .env automatically
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    BASE_DIR: Path = Path(__file__).parent

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

    # Pydantic will override these defaults from .env
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "testuser"
    SMTP_PASSWORD: str = "testpassword"
    SMTP_USE_TLS: bool = False

    PATH_TO_EMAIL_TEMPLATES_DIR: str = str(BASE_DIR / "auth" / "templates")
    ACTIVATION_EMAIL_TEMPLATE_NAME: str = "activation_request.html"
    ACTIVATION_COMPLETE_EMAIL_TEMPLATE_NAME: str = "activation_complete.html"
    PASSWORD_RESET_TEMPLATE_NAME: str = "password_reset_request.html"
    PASSWORD_RESET_COMPLETE_TEMPLATE_NAME: str = "password_reset_complete.html"


class Settings(BaseAppSettings):
    # Pydantic will override these defaults from .env
    POSTGRES_USER: str = "cinema_user"
    POSTGRES_PASSWORD: str = "cinema_password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_DB_PORT: int = 5432
    POSTGRES_DB: str = "cinema_db"

    JWT_SECRET_KEY_ACCESS: SecretStr = SecretStr("default_access")
    JWT_SECRET_KEY_REFRESH: SecretStr = SecretStr("default_refresh")
    JWT_SIGNING_ALGORITHM: str = "HS256"


def get_settings() -> BaseAppSettings:
    return Settings()
