from contextlib import asynccontextmanager
from fastapi import FastAPI

from database import init_db, close_db


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await init_db()
        yield
        await close_db()

    app = FastAPI(
        title="Online Cinema",
        description=(
            "A digital platform that allows users to select, watch, "
            "and purchase access to movies and other video materials "
            "via the internet."
        ),
        lifespan=lifespan
    )

    return app


app = create_app()


@app.get("/users/")
async def read_users():
    return {"message": "List of users"}
