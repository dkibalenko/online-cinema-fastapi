from fastapi import FastAPI
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

from pagination import setup_pagination
from logger_config import setup_logging
from rate_limiting import limiter

from auth.router import router as auth_router
from users.router import router as users_router
from users.admin.router import router as admin_router
from movies.router import router as movies_router
from movies.genres_router import router as genres_router
from notifications.ws_router import router as ws_router


def create_app(testing: bool = False) -> FastAPI:
    """
    Creates a FastAPI instance with the following configuration:
    - Logging is set up
    - The FastAPI instance has the title "Online Cinema" and a description
    - Debug mode is enabled if testing is True
    - The FastAPI instance includes routers for authentication, users,
        admin users, movies, and genres
    - The FastAPI instance includes a rate limiter and a middleware to handle
      rate limit exceeded exceptions, but only if testing is False

    Args:
        testing (bool): Whether to enable debug mode. Defaults to False.

    Returns:
        FastAPI: The created FastAPI instance
    """
    setup_logging()

    app = FastAPI(
        title="Online Cinema",
        description=(
            "A digital platform that allows users to select, watch, "
            "and purchase access to movies and other video materials "
            "via the internet."
        ),
        debug=testing,
    )

    # Pagination
    setup_pagination(app)

    # Routers
    api_version_prefix = "/api/v1/cinema"

    app.include_router(auth_router, prefix=f"{api_version_prefix}")
    app.include_router(users_router, prefix=f"{api_version_prefix}")
    app.include_router(admin_router, prefix=f"{api_version_prefix}")
    app.include_router(movies_router, prefix=f"{api_version_prefix}")
    app.include_router(genres_router, prefix=f"{api_version_prefix}")
    app.include_router(ws_router, prefix=f"{api_version_prefix}")

    # Rate limiting only in non‑test runs
    if not testing:
        app.state.limiter = limiter
        app.add_middleware(SlowAPIMiddleware)

        @app.exception_handler(RateLimitExceeded)
        async def rate_limit_handler(request, exc):
            return JSONResponse(
                status_code=429,
                content={
                    "message": "Too many requests. Please try again later."
                },
            )

    return app


app = create_app()
