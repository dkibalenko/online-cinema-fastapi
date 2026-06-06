from typing import Any

from sqlalchemy import Select, case, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from base_repository import BaseRepository
from movies.models import (
    FavoriteMovie,
    Genre,
    Movie,
    MovieComment,
    MovieLike,
    MovieRating,
    MoviesGenresModel,
)


class MovieRepository(BaseRepository):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def get_movie_by_id_with_relations(
        self, movie_id: int
    ) -> Movie | None:
        """Retrieve a movie by its id.

        This method includes the relationships:
        - certification
        - genres
        - directors
        - stars

        Args:
            movie_id (int): The id of the movie.

        Returns:
            Movie | None: The movie or None if not found.
        """
        stmt = (
            select(Movie)
            .options(
                joinedload(Movie.certification),
                selectinload(Movie.genres),
                selectinload(Movie.directors),
                selectinload(Movie.stars),
            )
            .where(Movie.id == movie_id)
        )
        result = await self.db.execute(stmt)
        return (
            result.unique().scalar_one_or_none()
        )  # for joinedload/selectinload

    async def get_movie_basic(self, movie_id: int) -> Movie | None:
        """Retrieve a movie by its id.

        This method does not include the relationships.

        Args:
            movie_id (int): The id of the movie.

        Returns:
            Movie | None: The movie or None if not found.
        """
        result = await self.db.execute(
            select(Movie).where(Movie.id == movie_id)
        )
        return (
            result.unique().scalar_one_or_none()
        )  # for joinedload/selectinload

    async def get_movie_by_name_year(
        self, name: str, year: int
    ) -> Movie | None:
        """Get a movie by its name and year.

        :param name: The name of the movie.
        :param year: The year of the movie.
        :return: The movie if found, otherwise None.
        """
        stmt = select(Movie).where(Movie.name == name, Movie.year == year)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_movies(self, stmt):
        """Execute a SQL query to retrieve a list of movies.

        :param stmt: The SQL query to execute.
        :return: The result of the query execution.
        """
        return await self.db.execute(stmt)

    async def refresh(self, instance: Any, attrs=None):
        await self.db.refresh(instance, attrs)

    async def refresh_with_relations(self, movie: Movie):
        """Refresh a movie instance with related objects.

        This method refreshes a movie instance with the related objects
        (certification, genres, directors, stars).

        :param movie: The movie instance to refresh.
        """
        await self.db.refresh(
            movie, ["certification", "genres", "directors", "stars"]
        )

    async def get_genres_with_movie_count(self) -> list[Row]:
        """Get a list of genres along with movies count associated with each.

        :return: A list of tuples containing the genre ID, name, & movie count.
        """
        # SQL logic:
        # SELECT genres.id, genres.name, count(movie_genres.movie_id)
        # FROM genres
        # LEFT JOIN movie_genres ON genres.id = movie_genres.genre_id
        # GROUP BY genres.id
        stmt = (
            select(
                Genre.id,
                Genre.name,
                func.count(MoviesGenresModel.c.movie_id).label("movie_count"),
            )
            .outerjoin(
                MoviesGenresModel, Genre.id == MoviesGenresModel.c.genre_id
            )
            .group_by(Genre.id, Genre.name)
            .order_by(func.count(MoviesGenresModel.c.movie_id).desc())
        )

        result = await self.db.execute(stmt)

        return list(result.all())

    async def upsert_movie_reaction(
        self, user_id: int, movie_id: int, is_like: bool
    ) -> None:
        """Upserts a movie reaction into the database.

        This method is atomic, and uses PostgreSQL's `ON CONFLICT DO UPDATE`
        clause to ensure that no race conditions occur, and no duplicate
        inserts are made.

        :param user_id: The user ID who reacted to the movie
        :param movie_id: The movie ID which the user reacted to
        :param is_like: A boolean indicating whether the reaction is
            a like or dislike
        :return: None
        """
        # atomic UPSERT moves concurrency control into PostgreSQL
        # no race, no duplicate inserts, no 500s
        stmt = (
            insert(MovieLike)
            .values(
                user_id=user_id,
                movie_id=movie_id,
                is_like=is_like,
            )
            .on_conflict_do_update(
                index_elements=[MovieLike.user_id, MovieLike.movie_id],
                set_={"is_like": is_like},
            )
        )
        await self.db.execute(stmt)

    async def remove_movie_reaction(self, user_id: int, movie_id: int) -> None:
        """Remove a movie reaction from a user.

        :param user_id: The user ID who reacted to the movie
        :param movie_id: The movie ID which the user reacted to

        :return: None
        """
        await self.db.execute(
            delete(MovieLike).where(
                MovieLike.user_id == user_id, MovieLike.movie_id == movie_id
            )
        )

    async def get_movie_reaction_counts(
        self, movie_id: int
    ) -> tuple[int, int]:
        """Get the counts of likes and dislikes for a movie.

        :param movie_id: The movie ID to get the reaction counts for.
        :return: A tuple containing the like count and dislike count.
        """
        # SELECT
        # SUM(CASE WHEN movie_likes.is_like = TRUE THEN 1 ELSE 0 END) AS sum_1,
        # SUM(CASE WHEN movie_likes.is_like = FALSE THEN 1 ELSE 0 END) AS sum_2
        # FROM movie_likes
        # WHERE movie_likes.movie_id = <movie_id>;
        stmt = select(
            # counts rows matching a condition
            func.sum(
                case((MovieLike.is_like.is_(True), 1), else_=0)
                # case((MovieLike.is_like == True, 1), else_=0)
            ),  # number of likes
            func.sum(
                case((MovieLike.is_like.is_(False), 1), else_=0)
                # case((MovieLike.is_like == False, 1), else_=0)
            ),  # number of dislikes
        ).where(MovieLike.movie_id == movie_id)
        result = await self.db.execute(stmt)
        likes, dislikes = (
            result.one()
        )  # always returns exactly one row - SUM() always returns a row

        return int(likes or 0), int(dislikes or 0)

    async def get_user_movie_reaction(
        self, user_id: int, movie_id: int
    ) -> bool | None:
        """Get the reaction of a user to a movie.

        :param user_id: The user ID who reacted to the movie
        :param movie_id: The movie ID which the user reacted to
        :return: Whether the user liked the movie (True),
            disliked the movie (False), or did not react to the movie (None)
        """
        stmt = select(MovieLike.is_like).where(
            MovieLike.user_id == user_id, MovieLike.movie_id == movie_id
        )
        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()  # True, False, or None

    async def upsert_movie_rating(
        self, user_id: int, movie_id: int, rating: int
    ) -> None:
        """Upserts a movie rating into the database.

        This method is atomic, and uses PostgreSQL's `ON CONFLICT DO UPDATE`
        clause to ensure that no race conditions occur, and no duplicate
        inserts are made.

        :param user_id: The user ID who rated the movie
        :param movie_id: The movie ID which the user rated
        :param rating: The rating value to update
        :return: None
        """
        # atomic UPSERT moves concurrency control into PostgreSQL
        # no race, no duplicate inserts, no 500s
        # INSERT INTO movie_ratings (...)
        # ON CONFLICT (user_id, movie_id)
        # DO UPDATE SET rating = EXCLUDED.rating;
        stmt = (
            insert(MovieRating)
            .values(
                user_id=user_id,
                movie_id=movie_id,
                rating=rating,
            )
            .on_conflict_do_update(
                index_elements=[MovieRating.user_id, MovieRating.movie_id],
                set_={"rating": rating},
            )
        )
        await self.db.execute(stmt)

    async def delete_movie_rating(self, user_id: int, movie_id: int) -> None:
        """Delete a movie rating from a user.

        :param user_id: The user ID who rated the movie
        :param movie_id: The movie ID which the user rated
        :return: None
        """
        await self.db.execute(
            delete(MovieRating).where(
                MovieRating.user_id == user_id, MovieRating.movie_id == movie_id
            )
        )

    async def get_movie_rating_summary(
        self, user_id: int, movie_id: int
    ) -> tuple[float | None, int, int | None]:
        """Get the summary of movie ratings for a movie.

        :param user_id: The user ID to get the user's rating for.
        :param movie_id: The movie ID to get the ratings summary for.
        :return: A tuple containing the average rating, the count of ratings,
            and the user's rating.
        """
        # aggregate
        # SELECT
        #     AVG(movie_ratings.rating) AS avg_rating,
        #     COUNT(movie_ratings.rating) AS count_rating
        # FROM movie_ratings
        # WHERE movie_ratings.movie_id = :movie_id;
        agg_stmt = select(
            func.avg(MovieRating.rating),  # avg rating
            func.count(MovieRating.rating),  # rating count
        ).where(MovieRating.movie_id == movie_id)

        agg_result = await self.db.execute(agg_stmt)
        avg_rating, count = agg_result.one()
        avg_rating = (
            float(avg_rating) if avg_rating is not None else None
        )  # AVG() returns NULL if no rows exist
        count = int(count or 0)  # COUNT() returns 0 if no rows exist

        # user rating
        # SELECT movie_ratings.rating
        # FROM movie_ratings
        # WHERE movie_ratings.user_id = :user_id AND
        # movie_ratings.movie_id = :movie_id; LOOKUP is VERY FAST since
        # user_id/movie_id form a composite PK key
        user_stmt = select(MovieRating.rating).where(
            MovieRating.user_id == user_id, MovieRating.movie_id == movie_id
        )
        user_result = await self.db.execute(user_stmt)
        user_rating = user_result.scalar_one_or_none()

        return avg_rating, count, user_rating

    async def add_favorite(self, user_id: int, movie_id: int) -> None:
        """Add a favorite movie to the user.

        :param user_id: The user ID to add the favorite movie to.
        :param movie_id: The movie ID to add as favorite.
        :return: None
        """
        stmt = (
            insert(FavoriteMovie)
            .values(user_id=user_id, movie_id=movie_id)
            .on_conflict_do_nothing(
                index_elements=[FavoriteMovie.user_id, FavoriteMovie.movie_id]
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def remove_favorite(self, user_id: int, movie_id: int) -> None:
        """Remove a favorite movie from the user.

        :param user_id: The user ID to remove the favorite movie from.
        :param movie_id: The movie ID to remove as favorite.
        :return: None
        """
        await self.db.execute(
            delete(FavoriteMovie).where(
                FavoriteMovie.user_id == user_id,
                FavoriteMovie.movie_id == movie_id,
            )
        )
        await self.db.flush()

    async def is_favorite(self, user_id: int, movie_id: int) -> bool:
        """Check if a movie is a favorite of the user.

        :param user_id: The user ID to check the favorite movie of.
        :param movie_id: The movie ID to check as favorite.
        :return: True if the movie is a favorite of the user, False otherwise.
        """
        stmt = select(FavoriteMovie).where(
            FavoriteMovie.user_id == user_id,
            FavoriteMovie.movie_id == movie_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_favorites_query(self, user_id: int) -> Select:
        """Get a query to retrieve favorite movies of a user.

        :param user_id: The user ID to retrieve the favorite movies of.
        :return: A SQLAlchemy query object.
        """
        return (
            select(Movie)
            .join(FavoriteMovie, FavoriteMovie.movie_id == Movie.id)
            .where(FavoriteMovie.user_id == user_id)
        )

    async def get_favorite_movie_ids(self, user_id: int) -> set[int]:
        """Retrieve the IDs of all favorite movies of a user.

        :param user_id: The user ID to retrieve the favorite movies of.
        :return: A set of movie IDs.
        """
        stmt = select(FavoriteMovie.movie_id).where(
            FavoriteMovie.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return {row[0] for row in result.all()}

    async def create_comment(
        self, movie_id: int, user_id: int, content: str, parent_id: int | None
    ) -> MovieComment:
        """Create a new comment for a specific movie.

        :param movie_id: The ID of the movie to create the comment for.
        :param user_id: The ID of the user creating the comment.
        :param content: The content of the comment.
        :param parent_id: The ID of the parent comment if this is a reply,
            None otherwise.
        :return: The created comment object.
        """
        comment = MovieComment(
            movie_id=movie_id,
            user_id=user_id,
            content=content,
            parent_id=parent_id,
        )
        self.db.add(comment)
        await self.db.flush()
        return comment

    async def get_comments_for_movie(  # fix with recursive CTE query
        self, movie_id: int
    ) -> list[MovieComment]:
        """Retrieve a list of comments for a specific movie.

        :param movie_id: The ID of the movie to retrieve comments for.
        :return: A list of comments for the movie.
        """
        stmt = (
            select(MovieComment)
            .where(MovieComment.movie_id == movie_id)
            .order_by(MovieComment.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_comment_by_id(self, comment_id: int) -> MovieComment | None:
        """Retrieve a comment by its ID.

        Fetches the comment along with the user who created it.

        :param comment_id: The ID of the comment to retrieve.
        :return: The comment object if found, None otherwise.
        """
        stmt = (
            select(MovieComment)
            .where(MovieComment.id == comment_id)
            .options(selectinload(MovieComment.user))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
