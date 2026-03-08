from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from cache.dependencies import get_cache
from cache.service import CacheService
from database import get_db
from movies.repository import MovieRepository
from movies.service import MovieService


def get_movie_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheService, Depends(get_cache)]
) -> MovieService:
    """Returns an instance of MovieService.

    Provides methods for interacting with the database in regards to movies.

    :param db: An async database session.
    :return: An instance of MovieService.
    """
    repo = MovieRepository(db)
    return MovieService(repo, cache)
