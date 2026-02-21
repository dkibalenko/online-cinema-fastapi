from typing import Any, Optional, List, Tuple

from sqlalchemy import select, func, case, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.engine import Row

from movies.models import (
    Movie,
    Genre,
    MoviesGenresModel,
    MovieLike,
    MovieRating,
    FavoriteMovie
)


class MovieRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_movie_by_id_with_relations(
        self,
        movie_id: int
    ) -> Optional[Movie]:
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
        return result.unique().scalar_one_or_none()  # for joinedload/selectinload

    async def get_movie_basic(self, movie_id: int) -> Optional[Movie]:
        result = await self.db.execute(
            select(Movie).where(Movie.id == movie_id)
        )
        return result.unique().scalar_one_or_none()  # for joinedload/selectinload

    async def get_movie_by_name_year(
        self,
        name: str,
        year: int
    ) -> Optional[Movie]:
        """
        Get a movie by its name and year.

        :param name: The name of the movie.
        :param year: The year of the movie.
        :return: The movie if found, otherwise None.
        """
        stmt = select(Movie).where(Movie.name == name, Movie.year == year)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_movies(self, stmt):
        return await self.db.execute(stmt)

    def add(self, instance: Any):
        self.db.add(instance)

    async def delete(self, instance: Any):
        await self.db.delete(instance)

    async def commit(self):
        await self.db.commit()

    async def rollback(self):
        await self.db.rollback()

    async def refresh(self, instance: Any, attrs=None):
        await self.db.refresh(instance, attrs)

    async def refresh_with_relations(self, movie: Movie):
        """
        Refresh a movie instance with related objects
        (certification, genres, directors, stars).

        :param movie: The movie instance to refresh.
        """
        await self.db.refresh(
            movie, ["certification", "genres", "directors", "stars"]
        )

    async def get_genres_with_movie_count(self) -> List[Row]:
        """
        Get a list of genres along with the count of movies associated with each.

        :return: A list of tuples containing the genre ID, name, and movie count.
        """
        # SQL logic: 
        # SELECT genres.id, genres.name, count(movie_genres.movie_id) 
        # FROM genres LEFT JOIN movie_genres ON genres.id = movie_genres.genre_id 
        # GROUP BY genres.id
        stmt = (
            select(
                Genre.id,
                Genre.name,
                func.count(MoviesGenresModel.c.movie_id).label("movie_count")
            )
            .outerjoin(
                MoviesGenresModel, Genre.id == MoviesGenresModel.c.genre_id
            )
            .group_by(Genre.id, Genre.name)
            .order_by(func.count(MoviesGenresModel.c.movie_id).desc())
        )

        result = await self.db.execute(stmt)

        return result.all()
    
    async def upsert_movie_reaction(
        self,
        user_id: int,
        movie_id: int,
        is_like: bool
    ) -> None:
        """
        Upsert a movie reaction from a user

        :param user_id: The user ID who reacted to the movie
        :param movie_id: The movie ID which the user reacted to
        :param is_like: Whether the user liked the movie

        :return: None
        """
        # 1. Check if the user has already reacted to the movie
        stmt = select(MovieLike).where(
            MovieLike.user_id == user_id,
            MovieLike.movie_id == movie_id
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        # 2. Update or insert the reaction
        if existing:
            existing.is_like = is_like
        else:
            self.db.add(
                MovieLike(
                    user_id=user_id,
                    movie_id=movie_id,
                    is_like=is_like
                )
            )

    async def remove_movie_reaction(
        self,
        user_id: int,
        movie_id: int
    ) -> None:
        """
        Remove a movie reaction from a user.

        :param user_id: The user ID who reacted to the movie
        :param movie_id: The movie ID which the user reacted to

        :return: None
        """
        # 1. Check if the user has already reacted to the movie
        stmt = select(MovieLike).where(
            MovieLike.user_id == user_id,
            MovieLike.movie_id == movie_id
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        # 2. Delete the reaction
        if existing:
            await self.db.delete(existing)

    async def get_movie_reaction_counts(
        self,
        movie_id: int
    ) -> Tuple[int, int]:
        """
        Get the counts of likes and dislikes for a movie.

        :param movie_id: The movie ID to get the reaction counts for.
        :return: A tuple containing the like count and dislike count.
        """
        # SELECT
        #     SUM(CASE WHEN movie_likes.is_like = TRUE THEN 1 ELSE 0 END) AS sum_1,
        #     SUM(CASE WHEN movie_likes.is_like = FALSE THEN 1 ELSE 0 END) AS sum_2
        # FROM movie_likes
        # WHERE movie_likes.movie_id = <movie_id>;
        stmt = (
            select(
                # counts rows matching a condition
                func.sum(case((MovieLike.is_like == True, 1), else_=0)),  # number of likes
                func.sum(case((MovieLike.is_like == False, 1), else_=0)),  # number of dislikes
            )
            .where(MovieLike.movie_id == movie_id)
        )
        result = await self.db.execute(stmt)
        likes, dislikes = result.one()  # always returns exactly one row - SUM() always returns a row

        return int(likes or 0), int(dislikes or 0)

    async def get_user_movie_reaction(
        self,
        user_id: int,
        movie_id: int
    ) -> bool | None:
        """
        Get the reaction of a user to a movie.

        :param user_id: The user ID who reacted to the movie
        :param movie_id: The movie ID which the user reacted to
        :return: Whether the user liked the movie (True),
            disliked the movie (False), or did not react to the movie (None)
        """
        stmt = select(MovieLike.is_like).where(
            MovieLike.user_id == user_id,
            MovieLike.movie_id == movie_id
        )
        result = await self.db.execute(stmt)
        value = result.scalar_one_or_none()

        return value  # True, False, or None

    async def upsert_movie_rating(
        self,
        user_id: int,
        movie_id: int,
        rating: int
    ) -> None:
        """
        Upsert a movie rating from a user

        :param user_id: The user ID who rated the movie
        :param movie_id: The movie ID which the user rated
        :param rating: The rating given by the user

        :return: None
        """
        # 1. Check if the user has already rated the movie
        stmt = select(MovieRating).where(
            MovieRating.user_id == user_id,
            MovieRating.movie_id == movie_id
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        # 2. Update or insert the rating
        if existing:
            existing.rating = rating
        else:
            self.db.add(
                MovieRating(
                    user_id=user_id,
                    movie_id=movie_id,
                    rating=rating
                )
            )

        await self.db.flush()

    async def delete_movie_rating(
        self,
        user_id: int,
        movie_id: int
    ) -> None:
        """
        Delete a movie rating from a user.

        :param user_id: The user ID who rated the movie
        :param movie_id: The movie ID which the user rated
        :return: None
        """
        stmt = select(MovieRating).where(
            MovieRating.user_id == user_id,
            MovieRating.movie_id == movie_id
        )
        result = await self.db.execute(stmt)
        rating = result.scalar_one_or_none()

        if rating:
            await self.db.delete(rating)
            await self.db.flush()

    async def get_movie_rating_summary(
        self,
        user_id: int,
        movie_id: int
    ) -> tuple[float | None, int, int | None]:
        """
        Get the summary of movie ratings for a movie.

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
            func.count(MovieRating.rating)  # rating count
        ).where(MovieRating.movie_id == movie_id)

        agg_result = await self.db.execute(agg_stmt)
        avg_rating, count = agg_result.one()
        avg_rating = float(avg_rating) if avg_rating is not None else None  # AVG() returns NULL if no rows exist
        count = int(count or 0)  # COUNT() returns 0 if no rows exist

        # user rating
        # SELECT movie_ratings.rating
        # FROM movie_ratings
        # WHERE movie_ratings.user_id = :user_id AND movie_ratings.movie_id = :movie_id; LOOKUP is VERY FAST since user_id/movie_id form a composite PK key
        user_stmt = select(MovieRating.rating).where(
            MovieRating.user_id == user_id,
            MovieRating.movie_id == movie_id
        )
        user_result = await self.db.execute(user_stmt)
        user_rating = user_result.scalar_one_or_none()

        return avg_rating, count, user_rating

    async def add_favorite(self, user_id: int, movie_id: int) -> None:
        """
        Add a favorite movie to the user.

        :param user_id: The user ID to add the favorite movie to.
        :param movie_id: The movie ID to add as favorite.
        :return: None
        """
        stmt = select(FavoriteMovie).where(
            FavoriteMovie.user_id == user_id,
            FavoriteMovie.movie_id == movie_id
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            self.db.add(FavoriteMovie(user_id=user_id, movie_id=movie_id))
            await self.db.flush()

    async def remove_favorite(self, user_id: int, movie_id: int) -> None:
        """
        Remove a favorite movie from the user.

        :param user_id: The user ID to remove the favorite movie from.
        :param movie_id: The movie ID to remove as favorite.
        :return: None
        """
        stmt = select(FavoriteMovie).where(
            FavoriteMovie.user_id == user_id,
            FavoriteMovie.movie_id == movie_id
        )
        result = await self.db.execute(stmt)
        favovite = result.scalar_one_or_none()

        if favovite:
            await self.db.delete(favovite)
            await self.db.flush()

    async def is_favorite(self, user_id: int, movie_id: int) -> bool:
        """
        Check if a movie is a favorite of the user.

        :param user_id: The user ID to check the favorite movie of.
        :param movie_id: The movie ID to check as favorite.
        :return: True if the movie is a favorite of the user, False otherwise.
        """
        stmt = select(FavoriteMovie).where(
            FavoriteMovie.user_id == user_id,
            FavoriteMovie.movie_id == movie_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_favorites_query(self, user_id: int) -> Select:
        """
        Get a query to retrieve favorite movies of a user.

        :param user_id: The user ID to retrieve the favorite movies of.
        :return: A SQLAlchemy query object.
        """
        return (
            select(Movie)
            .join(FavoriteMovie, FavoriteMovie.movie_id == Movie.id)
            .where(FavoriteMovie.user_id == user_id)
        )

    async def get_favorite_movie_ids(self, user_id: int) -> set[int]:
        """
        Retrieve the IDs of all favorite movies of a user.

        :param user_id: The user ID to retrieve the favorite movies of.
        :return: A set of movie IDs.
        """
        stmt = (
            select(FavoriteMovie.movie_id)
            .where(FavoriteMovie.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return {row[0] for row in result.all()}
