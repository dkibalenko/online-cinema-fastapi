from fastapi import FastAPI
from fastapi_pagination import add_pagination


def setup_pagination(app: FastAPI) -> None:
    """Attach pagination to the FastAPI app."""
    add_pagination(app)
