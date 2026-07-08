import json
import logging.config
from pathlib import Path


def setup_logging() -> None:
    """Loads logging configuration from the external JSON file.

    Then applies it using dictConfig.
    If the configuration file is not found or an error occurs during loading,
    a basic logging configuration is set up with WARNING level, and a warning
    message is logged.
    """
    try:
        config_file = Path(__file__).parent / "config.json"
        if not config_file.exists():
            raise FileNotFoundError(f"Path {config_file} does not exist")

        with Path.open(config_file) as f_in:
            config = json.load(f_in)

        logging.config.dictConfig(config)
    except Exception as e:
        logging.basicConfig(level=logging.WARNING)
        logging.warning(
            f"Failed to load logging configuration from JSON. Error: {e}"
        )


def get_logger() -> logging.Logger:
    """Returns the main, configured 'app_logger' instance."""
    return logging.getLogger("app_logger")
