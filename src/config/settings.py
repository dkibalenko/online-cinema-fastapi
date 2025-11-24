import os
from pathlib import Path
from pydantic_settings import BaseSettings


class BaseAppSettings(BaseSettings):
    BASE_DIR: Path = Path(__file__).parent.parent
    PATH_TO_DB: str = str(
        BASE_DIR / "database" / "source" / "online_cinema.db"
    )
    CERT_CSV_PATH: str = str(
        BASE_DIR / "database" / "seed_data" / "certifications.csv"
    )
    MOVIE_CSV_PATH: str = str(
        BASE_DIR / "database" / "seed_data" / "movies.csv"
    )


class Settings(BaseAppSettings):
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "cinema_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "cinema_password")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "cinema_host")
    POSTGRES_DB_PORT: int = int(os.getenv("POSTGRES_DB_PORT", 5432))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "cinema_db")


class TestingSettings(BaseAppSettings):
    PATH_TO_DB: str = ":memory:"


def get_settings() -> BaseSettings:
    """
    Retrieve the application settings based on the environment.

    This function checks the `ENVIRONMENT` environment variable to determine
    which settings class to use. If `ENVIRONMENT` is set to `"testing"`, it
    returns an instance of `TestingSettings`. Otherwise, it defaults to 
    `Settings`.

    :return: An instance of the appropriate settings class.
    :rtype: Settings
    """
    environment = os.getenv("ENVIRONMENT", "developing")
    if environment == "testing":
        return TestingSettings()
    return Settings()
