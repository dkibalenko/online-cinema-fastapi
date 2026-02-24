from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from fastapi_pagination.ext.sqlalchemy import paginate

from logger_config import get_logger

from cinema_celery.tasks.comment_tasks import send_comment_reply_notification
from notifications.websocket_manager import manager
from movies.repository import MovieRepository
from movies.utils import get_or_create_related
from movies.filters import build_movie_filter_query
from movies.models import Movie, Genre, Star, Director, Certification
from movies.schemas import (
    MovieCreateSchema,
    MovieUpdateSchema,
    GenreWithCountSchema,
    MovieReactionSummarySchema,
    MovieReactionActionResponseSchema,
    MovieRatingCreateSchema,
    MovieRatingSummarySchema,
    FavoriteMovieResponseSchema,
    MovieFilterParams,
    MovieSortParams,
    MovieDetailSchema,
    CommentCreateSchema,
    CommentSchema,
)

log = get_logger()


class MovieService:
    def __init__(self, repo: MovieRepository):
        self.repo = repo

    async def get_movie_list(
        self,
        user_id: int,
        filter_query: MovieFilterParams,
        sort_query: MovieSortParams
    ):
        """
        Fetches a list of movies based on the given filters and sort order

        Parameters:
            user_id (int): The ID of the user to fetch favorite movies for
            filter_query (MovieFilterParams): The filters to apply to
                the movie list
            sort_query (MovieSortParams): The sort order to apply to
                the movie list

        Returns:
            Page[MovieDetailSchema]: A paginated list of movies with their
                favorite status
        """
        log.info("Fetching movie list")
        filtered_query = build_movie_filter_query(filter_query, sort_query)

        page = await paginate(self.repo.db, filtered_query)

        favorite_ids = await self.repo.get_favorite_movie_ids(user_id)

        for movie in page.items:
            # efficiently compute is_favorite by a bulk lookup of user's favorite movie IDs
            movie.is_favorite = movie.id in favorite_ids

        return page

    async def get_movie_detail(
        self,
        movie_id: int,
        user_id: int
    ) -> MovieDetailSchema:
        """
        Fetches a movie by its ID, including its favorite status for
            the given user

        Parameters:
            movie_id (int): The ID of the movie to fetch
            user_id (int): The ID of the user to fetch favorite status for

        Returns:
            MovieDetailSchema: A movie with its favorite status
        """
        log.info(f"Fetching movie detail | movie_id={movie_id}")
        movie = await self.repo.get_movie_by_id_with_relations(movie_id)

        if not movie:
            log.warning(f"Movie not found | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found."
            )

        is_favorite = await self.repo.is_favorite(user_id, movie_id)

        return MovieDetailSchema(
            **movie.__dict__,
            is_favorite=is_favorite
        )

    async def create_movie(self, data: MovieCreateSchema) -> Movie:
        """
        Create a new movie.

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
                f"{data.year} already exists."
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
            # exclude the relation fields from the dict and pass resolved objects
            movie_dict = data.model_dump(  # gives a dict of validated data
                exclude={"genres", "stars", "directors", "certification"}
            )
            movie = Movie(
                **movie_dict,
                certification=certification,
                genres=genres,
                stars=stars,
                directors=directors
            )

            self.repo.add(movie)
            await self.repo.commit()

            # Refresh with joined/selectin data for the response
            await self.repo.refresh_with_relations(movie)

            log.info(f"Movie created | movie_id={movie.id}")
            return movie
        except IntegrityError as e:
            log.error(f"Integrity error during movie creation | error={e}")
            await self.repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Integrity error. Ensure all related data is valid."
            )

    async def update_movie(
        self,
        movie_id: int,
        data: MovieUpdateSchema
    ) -> Movie:
        """
        Update a movie by its ID.

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
                detail=f"Movie with ID {movie_id} not found."
            )

        # Extract only the fields sent in the request
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            log.warning(f"No fields provided for update | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update."
            )

        # Apply changes
        for field, value in update_data.items():
            setattr(movie, field, value)

        try:
            await self.repo.commit()
            # Refresh to get any server-side computed values
            await self.repo.refresh_with_relations(movie)

            log.info(f"Movie updated | movie_id={movie.id}")
            return movie
        except IntegrityError as e:
            log.error(f"Integrity error during movie update | error={e}")
            await self.repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Integrity error. Ensure all related data is unique/valid."
                )
            )

    async def delete_movie(self, movie_id: int):
        """
        Delete a movie by its ID.

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
                detail=f"Movie with ID {movie_id} not found."
            )

        await self.repo.delete(movie)
        await self.repo.commit()

        log.info(f"Movie deleted | movie_id={movie_id}")

    async def list_genres_with_count(self) -> list[GenreWithCountSchema]:
        """
        List all genres along with the count of movies associated with each.

        :return: A list of GenreWithCountSchema objects.
        """
        rows = await self.repo.get_genres_with_movie_count()

        return [
            GenreWithCountSchema(
                id=row.id,
                name=row.name,
                movie_count=row.movie_count
            )
            for row in rows
        ]

    async def _ensure_movie_exists(self, movie_id: int) -> None:
        movie = await self.repo.get_movie_basic(movie_id)

        if not movie:
            log.warning(f"Movie not found for reaction | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found."
            )

    async def _build_reaction_summary(
        self,
        user_id: int,
        movie_id: int
    ) -> MovieReactionSummarySchema:
        """
        Build a summary of reactions for a movie and a user.

        :param user_id: The ID of the user.
        :param movie_id: The ID of the movie.
        :return: A MovieReactionSummarySchema object.
        """
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

        return MovieReactionSummarySchema(
            movie_id=movie_id,
            likes=likes,
            dislikes=dislikes,
            user_reaction=reaction_str
        )

    async def like_movie(
        self,
        user_id: int,
        movie_id: int
    ) -> MovieReactionActionResponseSchema:
        """
        Like a movie.

        :param user_id: The ID of the user.
        :param movie_id: The ID of the movie.
        :return: A MovieReactionActionResponseSchema object.
        """
        log.info(f"Like movie | user_id={user_id} movie_id={movie_id}")
        await self._ensure_movie_exists(movie_id)

        await self.repo.upsert_movie_reaction(
            user_id=user_id,
            movie_id=movie_id,
            is_like=True
        )
        await self.repo.commit()

        summary = await self._build_reaction_summary(user_id, movie_id)
        return MovieReactionActionResponseSchema(
            movie_id=movie_id,
            action="like",
            likes=summary.likes,
            dislikes=summary.dislikes,
            user_reaction=summary.user_reaction
        )

    async def dislike_movie(
        self,
        user_id: int,
        movie_id: int
    ) -> MovieReactionActionResponseSchema:
        """
        Dislike a movie.

        :param user_id: The ID of the user.
        :param movie_id: The ID of the movie.
        :return: A MovieReactionActionResponseSchema object.
        """
        log.info(f"Dislike movie | user_id={user_id} movie_id={movie_id}")
        await self._ensure_movie_exists(movie_id)

        await self.repo.upsert_movie_reaction(
            user_id=user_id,
            movie_id=movie_id,
            is_like=False
        )
        await self.repo.commit()

        summary = await self._build_reaction_summary(user_id, movie_id)
        return MovieReactionActionResponseSchema(
            movie_id=movie_id,
            action="dislike",
            likes=summary.likes,
            dislikes=summary.dislikes,
            user_reaction=summary.user_reaction
        )

    async def remove_movie_reaction(
        self,
        user_id: int,
        movie_id: int
    ) -> MovieReactionActionResponseSchema:
        """
        Remove a reaction from a movie.

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

        summary = await self._build_reaction_summary(user_id, movie_id)
        return MovieReactionActionResponseSchema(
            movie_id=movie_id,
            action="removed",
            likes=summary.likes,
            dislikes=summary.dislikes,
            user_reaction=summary.user_reaction
        )

    async def get_movie_reactions(
        self,
        user_id: int,
        movie_id: int
    ) -> MovieReactionSummarySchema:
        """
        Get reactions summary for a movie.

        :param user_id: The ID of the user.
        :param movie_id: The ID of the movie.
        :return: A MovieReactionSummarySchema object.
        """
        log.info(
            f"Fetching movie reactions | user_id={user_id} movie_id={movie_id}"
        )
        movie = await self.repo.get_movie_basic(movie_id)
        if not movie:
            log.warning(f"Movie not found for reaction | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found."
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

        return MovieReactionSummarySchema(
            movie_id=movie_id,
            likes=likes,
            dislikes=dislikes,
            user_reaction=reaction
        )

    async def rate_movie(
        self,
        user_id: int,
        movie_id: int,
        payload: MovieRatingCreateSchema
    ) -> MovieRatingSummarySchema:
        """
        Rate a movie.

        :param user_id: The ID of the user.
        :param movie_id: The ID of the movie.
        :param payload: The rating given by the user.
        :return: A MovieRatingSummarySchema object.
        """
        log.info(f"Rate movie | user_id={user_id} movie_id={movie_id}")
        movie = await self.repo.get_movie_basic(movie_id)
        if not movie:
            log.warning(f"Movie not found for rating | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found."
            )

        await self.repo.upsert_movie_rating(
            user_id=user_id,
            movie_id=movie_id,
            rating=payload.rating
        )

        await self.repo.commit()

        avg_rating, count, user_rating = (
            await self.repo.get_movie_rating_summary(
                user_id=user_id,
                movie_id=movie_id
            )
        )

        return MovieRatingSummarySchema(
            movie_id=movie_id,
            average_rating=avg_rating,
            ratings_count=count,
            user_rating=user_rating
        )

    async def delete_movie_rating(
        self,
        user_id: int,
        movie_id: int
    ) -> MovieRatingSummarySchema:
        """
        Delete a movie rating from a user.

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
                detail=f"Movie with ID {movie_id} not found."
            )

        await self.repo.delete_movie_rating(user_id=user_id, movie_id=movie_id)

        await self.repo.commit()

        avg_rating, count, user_rating = (
                await self.repo.get_movie_rating_summary(
                user_id=user_id,
                movie_id=movie_id
            )
        )

        return MovieRatingSummarySchema(
            movie_id=movie_id,
            average_rating=avg_rating,
            ratings_count=count,
            user_rating=user_rating
        )

    async def get_movie_rating_summary(
        self,
        user_id: int,
        movie_id: int
    ) -> MovieRatingSummarySchema:
        """
        Get movie rating summary.

        :param user_id: The ID of the user.
        :param movie_id: The ID of the movie.
        :return: A MovieRatingSummarySchema object.
        """
        log.info(
            f"Get movie rating summary | user_id={user_id} movie_id={movie_id}"
        )
        movie = await self.repo.get_movie_basic(movie_id)
        if not movie:
            log.warning(f"Movie not found for rating | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found."
            )

        avg_rating, count, user_rating = (
                await self.repo.get_movie_rating_summary(
                user_id=user_id,
                movie_id=movie_id
            )
        )

        return MovieRatingSummarySchema(
            movie_id=movie_id,
            average_rating=avg_rating,
            ratings_count=count,
            user_rating=user_rating
        )

    async def add_to_favorites(
        self,
        user_id: int,
        movie_id: int
    ) -> FavoriteMovieResponseSchema:
        """
        Add a movie to user's favorites.

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
                detail=f"Movie with ID {movie_id} not found."
            )

        await self.repo.add_favorite(user_id, movie_id)
        await self.repo.commit()

        return FavoriteMovieResponseSchema(movie_id=movie_id, is_favorite=True)

    async def remove_from_favorites(
        self,
        user_id: int,
        movie_id: int
    ) -> FavoriteMovieResponseSchema:
        """
        Remove a movie from user's favorites.

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
                detail=f"Movie with ID {movie_id} not found."
            )

        await self.repo.remove_favorite(user_id, movie_id)
        await self.repo.commit()

        return FavoriteMovieResponseSchema(
            movie_id=movie_id, is_favorite=False
        )

    async def list_favorites(
        self,
        user_id: int,
        filter_query: MovieFilterParams,
        sort_query: MovieSortParams,
    ):
        base_query = await self.repo.get_favorites_query(user_id)

        filtered_query = build_movie_filter_query(
            filter_query=filter_query,
            sort_query=sort_query,
            base_query=base_query
        )

        return await paginate(self.repo.db, filtered_query)

    async def add_comment(
        self,
        movie_id: int,
        user_id: int,
        payload: CommentCreateSchema
    ) -> CommentSchema:
        log.info(f"Adding comment | movie_id={movie_id} user_id={user_id}")
        movie = await self.repo.get_movie_basic(movie_id)
        if not movie:
            log.warning(f"Movie not found for comment | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movie with ID {movie_id} not found."
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
                    detail="Invalid parent comment | "
                )

        comment = await self.repo.create_comment(
            movie_id=movie_id,
            user_id=user_id,
            content=payload.content,
            parent_id=payload.parent_id
        )

        await self.repo.commit()

        # side effects for notifications
        if parent:
            # fire-and-forget notification
            send_comment_reply_notification.delay(
                email=parent.user.email,
                movie_title=movie.name,
                reply_content=payload.content
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
                    "created_at": comment.created_at.isoformat()
                }
            )

        return CommentSchema.model_validate(comment)

    async def list_comments(
        self,
        movie_id: int
    ) -> list[CommentSchema]:
        log.info(f"Listing comments | movie_id={movie_id}")
        movie = await self.repo.get_movie_basic(movie_id)
        if not movie:
            log.warning(f"Movie not found for comment | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_404,
                detail=f"Movie with ID {movie_id} not found."
            )

        comments = await self.repo.get_comments_for_movie(movie_id)

        return [CommentSchema.model_validate(c) for c in comments]
