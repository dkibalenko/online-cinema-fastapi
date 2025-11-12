import os
from pathlib import Path
from pydantic_settings import BaseSettings


class BaseAppSettings(BaseSettings):
    BASE_DIR: Path(__file__).parent.parent
    PATH_TO_DB: str = str(
        BASE_DIR / "database" / "source" / "online_cinema.db"
    )
    PATH_TO_MOVIES_CSV: str = str(
        BASE_DIR / "database" / "seed_data" / "imdb_movies.csv"
    )


class TestingSettings(BaseAppSettings):
    PATH_TO_DB: str = ":memory:"


def get_settings() -> BaseSettings:
    """
    Retrieve the application settings based on the environment.

    This function checks the `ENVIRONMENT` environment variable to determine
    which settings class to use. If `ENVIRONMENT` is set to `"testing"`, it
    returns an instance of `TestingSettings`. Otherwise, it defaults to 
    `BaseAppSettings`.

    :return: An instance of the appropriate settings class.
    :rtype: BaseSettings
    """
    environment = os.getenv("ENVIRONMENT", "developing")
    if environment == "testing":
        return TestingSettings()
    return BaseAppSettings()
