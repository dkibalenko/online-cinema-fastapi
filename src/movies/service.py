from sqlalchemy.ext.asyncio import AsyncSession


class MovieService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # CRUD, search, filter, etc. will go here
