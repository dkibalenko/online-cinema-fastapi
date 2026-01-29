# src/main.py
from fastapi import FastAPI
from slowapi.middleware import SlowAPIMiddleware

from pagination import setup_pagination
from logger_config import setup_logging
from rate_limiting import limiter

# from auth.router import router as auth_router
from movies.router import router as movies_router
from movies.genres_router import router as genres_router


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title="Online Cinema",
        description=(
            "A digital platform that allows users to select, watch, "
            "and purchase access to movies and other video materials "
            "via the internet."
        ),
    )

    # Pagination
    setup_pagination(app)

    # Routers
    api_version_prefix = "/api/v1/cinema"

    # app.include_router(
    #     auth_router, prefix=f"{api_version_prefix}/auth", tags=["auth"]
    # )
    app.include_router(
        movies_router, prefix=f"{api_version_prefix}/movies", tags=["movies"]
    )
    app.include_router(
        genres_router, prefix=f"{api_version_prefix}/genres", tags=["genres"]
    )

    # Middleware
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    return app


app = create_app()
