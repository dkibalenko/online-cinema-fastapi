from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from movies.repository import MovieRepository
from movies.service import MovieService


def get_movie_service(
    db: AsyncSession = Depends(get_db)
) -> MovieService:
    """
    Returns an instance of MovieService, which provides methods for
    interacting with the database in regards to movies.

    :param db: An async database session.
    :return: An instance of MovieService.
    """
    repo = MovieRepository(db)
    return MovieService(repo)
