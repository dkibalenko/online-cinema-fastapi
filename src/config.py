# src/config.py
import os
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import SecretStr


class BaseAppSettings(BaseSettings):
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


class Settings(BaseAppSettings):
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "cinema_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "cinema_password")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "cinema_host")
    POSTGRES_DB_PORT: int = int(os.getenv("POSTGRES_DB_PORT", 5432))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "cinema_db")

    JWT_SECRET_KEY_ACCESS: SecretStr = SecretStr(
        os.getenv("JWT_SECRET_KEY_ACCESS", os.urandom(32).hex())
    )
    JWT_SECRET_KEY_REFRESH: SecretStr = SecretStr(
        os.getenv("JWT_SECRET_KEY_REFRESH", os.urandom(32).hex())
    )
    JWT_SIGNING_ALGORITHM: str = os.getenv(
        "JWT_SIGNING_ALGORITHM", "HS256"
    )


def get_settings() -> BaseAppSettings:
    """
    Retrieve the application settings based on the environment.

    ENVIRONMENT = "testing" -> TestingSettings
    otherwise -> Settings
    """
    return Settings()
