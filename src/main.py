from fastapi import FastAPI


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
