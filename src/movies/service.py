import hashlib
import json

from fastapi import HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.exc import IntegrityError

from cache.service import CacheService
from cinema_celery.tasks.comment_tasks import send_comment_reply_notification
from logger_config import get_logger
from movies.filters import build_movie_filter_query
from movies.models import Certification, Director, Genre, Movie, Star
from movies.repository import MovieRepository
from movies.schemas import (
    CommentCreateSchema,
    CommentSchema,
    FavoriteMovieResponseSchema,
    GenreWithCountSchema,
    MovieCreateSchema,
    MovieDetailSchema,
    MovieFilterParams,
    MovieRatingCreateSchema,
    MovieRatingSummarySchema,
    MovieReactionActionResponseSchema,
    MovieReactionSummarySchema,
    MovieSortParams,
    MovieUpdateSchema,
)
from movies.utils import get_or_create_related
from notifications.websocket_manager import manager

log = get_logger()


class MovieCacheInvalidationService:
    def __init__(self, cache: CacheService):
        self.cache = cache

    async def invalidate_movie_lists(self, user_id: int | None = None):
        """Invalidate all movie lists for a user.

        If user_id is None, invalidate all movie lists.
        Otherwise, invalidate only the movie lists for the given user.

        Args:
            user_id (int | None): The ID of the user. If None, invalidate all
            movie lists.
        """
        if user_id:
            await self.cache.delete_pattern(f"movies:list:{user_id}:*")
        else:
            await self.cache.delete_pattern("movies:list:*")

    async def invalidate_reactions(self, movie_id: int, user_id: int):
        """Invalidate reaction summary for a user.

        Args:
            movie_id (int): The ID of the movie.
            user_id (int): The ID of the user.
        """
        await self.cache.delete(f"movie:{movie_id}:reactions:user:{user_id}")

    async def invalidate_rating(self, movie_id: int, user_id: int):
        """Invalidate the rating summary for a user.

        Args:
            movie_id (int): The ID of the movie.
            user_id (int): The ID of the user.

        Returns:
            None
        """
        await self.cache.delete(
            f"movie:{movie_id}:rating_summary:user:{user_id}"
        )


class MovieService:
    def __init__(
        self,
        repo: MovieRepository,
        cache: CacheService,
        cache_invalidator: MovieCacheInvalidationService,
    ):
        self.repo = repo
        self.cache = cache
        self.cache_invalidator = cache_invalidator

    async def get_movie_list(
        self,
        user_id: int,
        filter_query: MovieFilterParams,
        sort_query: MovieSortParams,
    ):
        """Retrieve a paginated movie list with optional filtering & sorting.

        Args:
            user_id (int): The ID of the authenticated user.
            filter_query (MovieFilterParams): The filter options.
            sort_query (MovieSortParams): The sorting options.

        Returns:
            Page[MovieListItemSchema]: The paginated list of movies.
        """
        log.info("Fetching movie list")

        # Build a stable hash for filters + sorting + page
        filter_data = filter_query.model_dump()
        sort_data = sort_query.model_dump()

        # Convert to JSON string for hashing
        raw_key = json.dumps(
            {
                "filters": filter_data,
                "sort": sort_data,
            },
            sort_keys=True,
        )

        hashed = hashlib.md5(raw_key.encode()).hexdigest()

        cache_key = f"movies:list:{user_id}:{hashed}"

        cached = await self.cache.get(cache_key)
        if cached:
            # Reconstruct pagination object
            return Page(**cached)

        # Not cached → compute
        filtered_query = build_movie_filter_query(filter_query, sort_query)

        page = await paginate(self.repo.db, filtered_query)

        favorite_ids = await self.repo.get_favorite_movie_ids(user_id)

        for movie in page.items:
            # efficiently compute is_favorite by a bulk lookup of user's
            # favorite movie IDs
            movie.is_favorite = movie.id in favorite_ids

        # Cache the serialized page
        await self.cache.set(
            cache_key,
            page.model_dump(),
            ttl=60,  # 1 minute
        )

        return page

    async def get_movie_detail(
        self, movie_id: int, user_id: int
    ) -> MovieDetailSchema:
        """Retrieve a movie detail with optional filtering and sorting.

        Args:
            movie_id (int): The ID of the movie.
            user_id (int): The ID of the authenticated user.

        Returns:
            MovieDetailSchema: The movie detail.
        """
        log.info(f"Fetching movie detail | movie_id={movie_id}")

        cache_key = f"movie:detail:{movie_id}:user:{user_id}"
        cached = await self.cache.get(cache_key)
        if cached:
            return MovieDetailSchema(**cached)

        movie = await self.repo.get_movie_by_id_with_relations(movie_id)

        if not movie:
            log.warning(f"Movie not found | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found.",
            )

        is_favorite = await self.repo.is_favorite(user_id, movie_id)

        result = MovieDetailSchema(**movie.__dict__, is_favorite=is_favorite)

        await self.cache.set(cache_key, result.model_dump(), ttl=600)
        return result

    async def create_movie(self, data: MovieCreateSchema) -> Movie:
        """Create a new movie.

        :param data: The movie data to create.
        :raises HTTPException: If the movie already exists with the same
            name and year.
        :raises HTTPException: If any of the related data is invalid.
        :return: The newly created movie.
        """
        log.info(f"Creating movie | name={data.name} year={data.year}")

        # 1. Check for existing movie
        existing = await self.repo.get_movie_by_name_year(data.name, data.year)

        if existing:
            log.warning(
                f"Duplicate movie creation attempt | name={data.name} "
                f"year={data.year}"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Movie with the name {data.name} and year "
                f"{data.year} already exists.",
            )

        try:
            # 2. Handle Certification (Get or Create)
            certification = (
                await get_or_create_related(
                    Certification, [data.certification], self.repo.db
                )
            )[0]
            # 3. Resolve Many-to-Many Collections efficiently
            genres = await get_or_create_related(
                Genre, data.genres, self.repo.db
            )
            stars = await get_or_create_related(Star, data.stars, self.repo.db)
            directors = await get_or_create_related(
                Director, data.directors, self.repo.db
            )

            # 4. Create Movie
            # exclude the relation fields from the dict and pass resolved objs
            movie_dict = data.model_dump(  # gives a dict of validated data
                exclude={"genres", "stars", "directors", "certification"}
            )
            movie = Movie(
                **movie_dict,
                certification=certification,
                genres=genres,
                stars=stars,
                directors=directors,
            )

            self.repo.add(movie)
            await self.repo.commit()

            # Refresh with joined/selectin data for the response
            await self.repo.refresh_with_relations(movie)

            log.info(f"Movie created | movie_id={movie.id}")

            # invalidate ALL movie list caches
            await self.cache_invalidator.invalidate_movie_lists()

            return movie
        except IntegrityError as e:
            log.error(f"Integrity error during movie creation | error={e}")
            await self.repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Integrity error. Ensure all related data is valid.",
            ) from e

    async def update_movie(
        self, movie_id: int, data: MovieUpdateSchema
    ) -> Movie:
        """Update a movie by its ID.

        :param movie_id: The ID of the movie to be updated.
        :param data: The fields to be updated with the new values.
        :return: The updated movie.

        :raises HTTPException: If the movie is not found.
        :raises HTTPException: If no fields are provided for update,
            or if there is an integrity error.
        """
        log.info(f"Updating movie | movie_id={movie_id}")
        movie = await self.repo.get_movie_basic(movie_id)

        if not movie:
            log.warning(f"Movie not found | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found.",
            )

        # Extract only the fields sent in the request
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            log.warning(f"No fields provided for update | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update.",
            )

        # Apply changes
        for field, value in update_data.items():
            setattr(movie, field, value)

        try:
            await self.repo.commit()
            # Refresh to get any server-side computed values
            await self.repo.refresh_with_relations(movie)

            log.info(f"Movie updated | movie_id={movie.id}")

            # invalidate ALL movie list caches
            await self.cache_invalidator.invalidate_movie_lists()

            return movie
        except IntegrityError as e:
            log.error(f"Integrity error during movie update | error={e}")
            await self.repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Integrity error. Ensure all related data is unique/valid."
                ),
            ) from e

    async def delete_movie(self, movie_id: int):
        """Delete a movie by its ID.

        :param movie_id: The ID of the movie to be deleted.
        :raises HTTPException: If the movie is not found.
        """
        log.info(f"Deleting movie | movie_id={movie_id}")
        movie = await self.repo.db.get(Movie, movie_id)

        if not movie:
            log.warning(
                f"Delete failed — movie not found | movie_id={movie_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found.",
            )

        await self.repo.delete(movie)
        await self.repo.commit()

        # invalidate ALL movie list caches
        await self.cache_invalidator.invalidate_movie_lists()

        log.info(f"Movie deleted | movie_id={movie_id}")

    async def list_genres_with_count(self) -> list[GenreWithCountSchema]:
        """List genres with their associated movie count.

        This function first checks the cache for the result.
        If not found, it queries the database and caches the result.

        :return: A list of GenreWithCountSchema objects.
        """
        cache_key = "genres:with_count"

        cached = await self.cache.get(cache_key)
        if cached:
            return [GenreWithCountSchema(**row) for row in cached]

        rows = await self.repo.get_genres_with_movie_count()

        result = [
            GenreWithCountSchema(
                id=row.id, name=row.name, movie_count=row.movie_count
            )
            for row in rows
        ]

        await self.cache.set(
            cache_key,
            [r.model_dump() for r in result],
            ttl=3600,  # 1 hour
        )
        return result


class MovieReactionService:
    def __init__(
        self,
        repo: MovieRepository,
        cache: CacheService,
        cache_invalidator: MovieCacheInvalidationService,
    ):
        self.repo = repo
        self.cache = cache
        self.cache_invalidator = cache_invalidator

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

        # short TTL – reactions change often
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
        await self.repo.commit()

        # invalidate reactions cache for this user+movie
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
        await self.repo.commit()

        # invalidate reactions cache for this user+movie
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

        # invalidate reactions cache for this user+movie
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

        cache_key = f"movie:{movie_id}:reactions:user:{user_id}"
        cached = await self.cache.get(cache_key)
        if cached:
            return MovieReactionSummarySchema(**cached)

        movie = await self.repo.get_movie_basic(movie_id)
        if not movie:
            log.warning(f"Movie not found for reaction | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found.",
            )

        likes, dislikes = await self.repo.get_movie_reaction_counts(movie_id)
        user_reaction = await self.repo.get_user_movie_reaction(
            user_id, movie_id
        )

        if user_reaction is True:
            reaction = "like"
        elif user_reaction is False:
            reaction = "dislike"
        else:
            reaction = None

        result = MovieReactionSummarySchema(
            movie_id=movie_id,
            likes=likes,
            dislikes=dislikes,
            user_reaction=reaction,
        )

        # short TTL because reactions change often
        await self.cache.set(cache_key, result.model_dump(), ttl=60)

        return result

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

        await self.repo.commit()

        # invalidate rating summary cache
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

        await self.repo.commit()

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
    ):
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


class MovieCommentService:
    def __init__(self, repo: MovieRepository):
        self.repo = repo

    async def add_comment(
        self, movie_id: int, user_id: int, payload: CommentCreateSchema
    ) -> CommentSchema:
        """Add a comment to a movie.

        :param movie_id: The ID of the movie.
        :param user_id: The ID of the user.
        :param payload: The comment data.
        :return: The created comment object.
        :raises HTTPException:
            - `404 Not Found` if the movie does not exist
            - `400 Bad Request` if the parent comment does not exist or does
                not belong to the same movie
        """
        log.info(f"Adding comment | movie_id={movie_id} user_id={user_id}")

        movie = await self.repo.get_movie_basic(movie_id)
        if not movie:
            log.warning(f"Movie not found for comment | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found.",
            )

        parent = None

        if payload.parent_id:
            parent = await self.repo.get_comment_by_id(payload.parent_id)
            if not parent or parent.movie_id != movie_id:
                log.warning(
                    f"Invalid parent comment | parent_id={payload.parent_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Invalid parent comment. Parent comment does not exist"
                        " or does not belong to the same movie."
                    ),
                )

        comment = await self.repo.create_comment(
            movie_id=movie_id,
            user_id=user_id,
            content=payload.content,
            parent_id=payload.parent_id,
        )

        await self.repo.commit()

        # side effects for notifications
        if parent:
            # fire-and-forget notification
            send_comment_reply_notification.delay(
                email=parent.user.email,
                movie_title=movie.name,
                reply_content=payload.content,
            )
            # WebSocket broadcasting for real‑time notifications
            await manager.send_to_user(
                parent.user_id,
                {
                    "type": "comment_reply",
                    "movie_id": movie_id,
                    "comment_id": comment.id,
                    "content": payload.content,
                    "parent_id": payload.parent_id,
                    "created_at": comment.created_at.isoformat(),
                },
            )

        return CommentSchema.model_validate(comment)

    async def list_comments(self, movie_id: int) -> list[CommentSchema]:
        """List comments for a specific movie.

        Args:
            movie_id (int): ID of the movie to list comments for.

        Returns:
            list[CommentSchema]: A list of comments for the movie.

        Raises:
            HTTPException: If the movie is not found.
        """
        log.info(f"Listing comments | movie_id={movie_id}")

        movie = await self.repo.get_movie_basic(movie_id)
        if not movie:
            log.warning(f"Movie not found for comment | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found.",
            )

        comments = await self.repo.get_comments_for_movie(movie_id)

        return [CommentSchema.model_validate(c) for c in comments]
