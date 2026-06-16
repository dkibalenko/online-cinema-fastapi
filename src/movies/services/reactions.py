from fastapi import HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.exc import IntegrityError

from cache.service import CacheService
from logger_config import get_logger
from movies.filters import build_movie_filter_query
from movies.repositories import MovieRepository
from movies.schemas import (
    FavoriteMovieListSchema,
    FavoriteMovieResponseSchema,
    MovieFilterParams,
    MovieRatingCreateSchema,
    MovieRatingSummarySchema,
    MovieReactionActionResponseSchema,
    MovieReactionSummarySchema,
    MovieSortParams,
)
from movies.services.cache import MovieCacheInvalidationService

log = get_logger()


class MovieReactionService:
    def __init__(
        self,
        repo: MovieRepository,
        cache: CacheService,
        cache_invalidator: MovieCacheInvalidationService,
        enable_cache: bool = True,
    ):
        self.repo = repo
        self.cache = cache
        self.cache_invalidator = cache_invalidator
        self.enable_cache = enable_cache

    async def _ensure_movie_exists(self, movie_id: int) -> None:
        movie = await self.repo.get_movie_basic(movie_id)
        if not movie:
            log.warning(f"Movie not found for reaction | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found.",
            )

    async def _build_reaction_summary(
        self, user_id: int, movie_id: int
    ) -> MovieReactionSummarySchema:
        cache_key = f"movie:{movie_id}:reactions:user:{user_id}"
        if self.enable_cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return MovieReactionSummarySchema(**cached)

        likes, dislikes = await self.repo.get_movie_reaction_counts(movie_id)
        user_reaction = await self.repo.get_user_movie_reaction(
            user_id, movie_id
        )

        if user_reaction is True:
            reaction_str = "like"
        elif user_reaction is False:
            reaction_str = "dislike"
        else:
            reaction_str = None

        result = MovieReactionSummarySchema(
            movie_id=movie_id,
            likes=likes,
            dislikes=dislikes,
            user_reaction=reaction_str,
        )

        if self.enable_cache:
            await self.cache.set(cache_key, result.model_dump(), ttl=60)
        return result

    async def like_movie(
        self, user_id: int, movie_id: int
    ) -> MovieReactionActionResponseSchema:
        """Like a movie.

        :param user_id: The ID of the user.
        :param movie_id: The ID of the movie.
        :return: A MovieReactionActionResponseSchema object.
        """
        log.info(f"Like movie | user_id={user_id} movie_id={movie_id}")
        await self._ensure_movie_exists(movie_id)

        await self.repo.upsert_movie_reaction(
            user_id=user_id, movie_id=movie_id, is_like=True
        )

        try:
            await self.repo.commit()
        except IntegrityError as e:
            log.warning(
                f"Like failed — already liked | user_id={user_id} "
                f"movie_id={movie_id}"
            )
            await self.repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already liked this movie.",
            ) from e

        await self.cache_invalidator.invalidate_reactions(movie_id, user_id)
        await self.cache_invalidator.invalidate_movie_lists(user_id)

        summary = await self._build_reaction_summary(user_id, movie_id)
        return MovieReactionActionResponseSchema(
            movie_id=movie_id,
            action="like",
            likes=summary.likes,
            dislikes=summary.dislikes,
            user_reaction=summary.user_reaction,
        )

    async def dislike_movie(
        self, user_id: int, movie_id: int
    ) -> MovieReactionActionResponseSchema:
        """Dislike a movie.

        :param user_id: The ID of the user.
        :param movie_id: The ID of the movie.
        :return: A MovieReactionActionResponseSchema object.
        """
        log.info(f"Dislike movie | user_id={user_id} movie_id={movie_id}")
        await self._ensure_movie_exists(movie_id)

        await self.repo.upsert_movie_reaction(
            user_id=user_id, movie_id=movie_id, is_like=False
        )

        try:
            await self.repo.commit()
        except IntegrityError as e:
            log.warning(
                f"Dislike failed — already disliked | user_id={user_id} "
                f"movie_id={movie_id}"
            )
            await self.repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Concurrent update conflict. Please retry.",
            ) from e

        await self.cache_invalidator.invalidate_reactions(movie_id, user_id)
        await self.cache_invalidator.invalidate_movie_lists(user_id)

        summary = await self._build_reaction_summary(user_id, movie_id)
        return MovieReactionActionResponseSchema(
            movie_id=movie_id,
            action="dislike",
            likes=summary.likes,
            dislikes=summary.dislikes,
            user_reaction=summary.user_reaction,
        )

    async def remove_movie_reaction(
        self, user_id: int, movie_id: int
    ) -> MovieReactionActionResponseSchema:
        """Remove a reaction from a movie.

        :param user_id: The ID of the user.
        :param movie_id: The ID of the movie.
        :return: A MovieReactionActionResponseSchema object.
        """
        log.info(
            f"Remove movie reaction | user_id={user_id} movie_id={movie_id}"
        )
        await self._ensure_movie_exists(movie_id)

        await self.repo.remove_movie_reaction(user_id, movie_id)
        await self.repo.commit()

        await self.cache_invalidator.invalidate_reactions(movie_id, user_id)
        await self.cache_invalidator.invalidate_movie_lists(user_id)

        summary = await self._build_reaction_summary(user_id, movie_id)
        return MovieReactionActionResponseSchema(
            movie_id=movie_id,
            action="removed",
            likes=summary.likes,
            dislikes=summary.dislikes,
            user_reaction=summary.user_reaction,
        )

    async def get_movie_reactions(
        self, user_id: int, movie_id: int
    ) -> MovieReactionSummarySchema:
        """Get reactions summary for a movie.

        :param user_id: The ID of the user.
        :param movie_id: The ID of the movie.
        :return: A MovieReactionSummarySchema object.
        """
        log.info(
            f"Fetching movie reactions | user_id={user_id} movie_id={movie_id}"
        )
        await self._ensure_movie_exists(movie_id)
        return await self._build_reaction_summary(user_id, movie_id)

    async def rate_movie(
        self, user_id: int, movie_id: int, payload: MovieRatingCreateSchema
    ) -> MovieRatingSummarySchema:
        """Rate a movie on a 1-10 scale.

        :param user_id: The ID of the user.
        :param movie_id: The ID of the movie.
        :param payload: A MovieRatingCreateSchema object containing the rating.
        :return: A MovieRatingSummarySchema object containing the updated
            rating summary.
        """
        log.info(f"Rate movie | user_id={user_id} movie_id={movie_id}")

        movie = await self.repo.get_movie_basic(movie_id)
        if not movie:
            log.warning(f"Movie not found for rating | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found.",
            )

        await self.repo.upsert_movie_rating(
            user_id=user_id, movie_id=movie_id, rating=payload.rating
        )

        try:
            await self.repo.commit()
        except IntegrityError as e:
            log.warning(
                f"Rating failed — already rated | user_id={user_id} "
                f"movie_id={movie_id}"
            )
            await self.repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Concurrent update conflict. Please retry.",
            ) from e

        await self.cache_invalidator.invalidate_rating(movie_id, user_id)
        await self.cache_invalidator.invalidate_movie_lists(user_id)

        (
            avg_rating,
            count,
            user_rating,
        ) = await self.repo.get_movie_rating_summary(
            user_id=user_id, movie_id=movie_id
        )

        return MovieRatingSummarySchema(
            movie_id=movie_id,
            average_rating=avg_rating,
            ratings_count=count,
            user_rating=user_rating,
        )

    async def delete_movie_rating(
        self, user_id: int, movie_id: int
    ) -> MovieRatingSummarySchema:
        """Delete a movie rating from a user.

        :param user_id: The ID of the user.
        :param movie_id: The ID of the movie.
        :return: A MovieRatingSummarySchema object.
        """
        log.info(
            f"Delete movie rating | user_id={user_id} movie_id={movie_id}"
        )

        movie = await self.repo.get_movie_basic(movie_id)
        if not movie:
            log.warning(f"Movie not found for rating | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found.",
            )

        await self.repo.delete_movie_rating(user_id=user_id, movie_id=movie_id)

        try:
            await self.repo.commit()
        except IntegrityError as e:
            log.warning(
                f"Rating delete failed | user_id={user_id} movie_id={movie_id}"
            )
            await self.repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Concurrent update conflict. Please retry.",
            ) from e

        await self.cache_invalidator.invalidate_movie_lists(user_id)

        (
            avg_rating,
            count,
            user_rating,
        ) = await self.repo.get_movie_rating_summary(
            user_id=user_id, movie_id=movie_id
        )

        return MovieRatingSummarySchema(
            movie_id=movie_id,
            average_rating=avg_rating,
            ratings_count=count,
            user_rating=user_rating,
        )

    async def get_movie_rating_summary(
        self, user_id: int, movie_id: int
    ) -> MovieRatingSummarySchema:
        """Retrieve a movie rating summary for a user.

        :param user_id: The ID of the user.
        :param movie_id: The ID of the movie.
        :return: A MovieRatingSummarySchema object.
        """
        log.info(
            f"Get movie rating summary | user_id={user_id} movie_id={movie_id}"
        )

        cache_key = f"movie:{movie_id}:rating_summary:user:{user_id}"
        if self.enable_cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return MovieRatingSummarySchema(**cached)

        movie = await self.repo.get_movie_basic(movie_id)
        if not movie:
            log.warning(f"Movie not found for rating | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found.",
            )

        (
            avg_rating,
            count,
            user_rating,
        ) = await self.repo.get_movie_rating_summary(
            user_id=user_id, movie_id=movie_id
        )

        result = MovieRatingSummarySchema(
            movie_id=movie_id,
            average_rating=avg_rating,
            ratings_count=count,
            user_rating=user_rating,
        )

        if self.enable_cache:
            await self.cache.set(cache_key, result.model_dump(), ttl=60)
        return result

    async def add_to_favorites(
        self, user_id: int, movie_id: int
    ) -> FavoriteMovieResponseSchema:
        """Add a movie to user's favorites.

        :param user_id: The ID of the user.
        :param movie_id: The ID of the movie to be added.
        :return: A FavoriteMovieResponseSchema object indicating whether
            the movie is in the user's favorites.
        """
        log.info(
            f"Adding movie to favorites | user_id={user_id} "
            f"movie_id={movie_id}"
        )

        movie = await self.repo.get_movie_basic(movie_id)
        if not movie:
            log.warning(f"Movie not found for favorite | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found.",
            )

        await self.repo.add_favorite(user_id, movie_id)
        await self.repo.commit()
        await self.cache_invalidator.invalidate_movie_lists(user_id)

        return FavoriteMovieResponseSchema(movie_id=movie_id, is_favorite=True)

    async def remove_from_favorites(
        self, user_id: int, movie_id: int
    ) -> FavoriteMovieResponseSchema:
        """Remove a movie from user's favorites.

        :param user_id: The ID of the user.
        :param movie_id: The ID of the movie to be removed.
        :return: A FavoriteMovieResponseSchema object indicating whether
            the movie is in the user's favorites.
        """
        log.info(
            f"Removing movie from favorites | user_id={user_id} "
            f"movie_id={movie_id}"
        )

        movie = await self.repo.get_movie_basic(movie_id)
        if not movie:
            log.warning(f"Movie not found for favorite | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found.",
            )

        await self.repo.remove_favorite(user_id, movie_id)
        await self.repo.commit()
        await self.cache_invalidator.invalidate_movie_lists(user_id)

        return FavoriteMovieResponseSchema(
            movie_id=movie_id, is_favorite=False
        )

    async def list_favorites(
        self,
        user_id: int,
        filter_query: MovieFilterParams,
        sort_query: MovieSortParams,
    ) -> Page[FavoriteMovieListSchema]:
        """Retrieve a paginated list of the user's favorite movies.

        :param user_id: The ID of the user.
        :param filter_query: The filter options.
        :param sort_query: The sorting options.

        :return: A paginated list of the user's favorite movies.
        """
        base_query = await self.repo.get_favorites_query(user_id)
        filtered_query = build_movie_filter_query(
            filter_query=filter_query,
            sort_query=sort_query,
            base_query=base_query,
        )
        return await paginate(self.repo.db, filtered_query)
