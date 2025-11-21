from fastapi import FastAPI

from logger_config import get_logger, setup_logging


setup_logging()
log = get_logger()


app = FastAPI(
    title="Online Cinema",
    description=(
        "A digital platform that allows users to select, watch, "
        "and purchase access to movies and other video materials "
        "via the internet."
    )
)


@app.get("/users/")
async def read_users():
    return {"message": "List of users"}
