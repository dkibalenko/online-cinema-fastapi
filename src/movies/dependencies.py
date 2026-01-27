# src/movies/dependencies.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from movies.service import MovieService


def get_movie_service(
    db: AsyncSession = Depends(get_db)
) -> MovieService:
    return MovieService(db)
