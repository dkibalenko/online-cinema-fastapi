from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from cache.dependencies import get_cache
from cache.service import CacheService
from config import BaseAppSettings, get_settings
from database import get_db
from movies.repositories import MovieRepository
from movies.repositories.video import VideoFileRepository
from movies.services import (
    MovieCacheInvalidationService,
    MovieCommentService,
    MovieReactionService,
    MovieService,
    VideoService,
)
from storages.dependencies import get_s3_storage_client
from storages.interfaces import S3StorageInterface


async def get_movie_cache_invalidation_service(
    cache: Annotated[CacheService, Depends(get_cache)],
) -> MovieCacheInvalidationService:
    """Returns an instance of MovieCacheInvalidationService.

    :param cache: An instance of CacheService.
    :return: An instance of MovieCacheInvalidationService.
    """
    return MovieCacheInvalidationService(cache)


async def get_movie_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheService, Depends(get_cache)],
    cache_invalidator: Annotated[
        MovieCacheInvalidationService,
        Depends(get_movie_cache_invalidation_service),
    ],
) -> MovieService:
    """Returns an instance of MovieService.

    Provides methods for interacting with the database in regards to movies.

    :param db: An async database session.
    :param cache: An instance of CacheService.
    :param cache_invalidator: An instance of MovieCacheInvalidationService.
    :return: An instance of MovieService.
    """
    repo = MovieRepository(db)
    return MovieService(
        repo,
        cache,
        cache_invalidator,
        # enable_cache=False,  # used for load testing
    )


async def get_movie_reaction_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheService, Depends(get_cache)],
    cache_invalidator: Annotated[
        MovieCacheInvalidationService,
        Depends(get_movie_cache_invalidation_service),
    ],
) -> MovieReactionService:
    """Returns an instance of MovieReactionService.

    Provides methods for interacting with the database in regards to movie
    reactions.

    :param db: An async database session.
    :param cache: An instance of CacheService.
    :param cache_invalidator: An instance of MovieCacheInvalidationService.
    :return: An instance of MovieReactionService.
    """
    repo = MovieRepository(db)
    return MovieReactionService(
        repo,
        cache,
        cache_invalidator,
        # enable_cache=False,  # used for load testing
    )


async def get_movie_comment_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MovieCommentService:
    """Returns an instance of MovieCommentService.

    Provides methods for interacting with the database in regards to movie
    comments.

    :param db: An async database session.
    :return: An instance of MovieCommentService.
    """
    repo = MovieRepository(db)
    return MovieCommentService(repo)


async def get_video_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    s3: Annotated[S3StorageInterface, Depends(get_s3_storage_client)],
    settings: Annotated[BaseAppSettings, Depends(get_settings)],
) -> VideoService:
    """Returns an instance of VideoService.

    Provides methods for video upload, transcode status, and stream URL.

    :param db: An async database session.
    :param s3: An S3 storage client.
    :param settings: Application settings.
    :return: An instance of VideoService.
    """
    repo = VideoFileRepository(db)
    return VideoService(repo, s3, settings)
