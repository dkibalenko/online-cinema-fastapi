from typing import Any, Optional, List, Tuple

from sqlalchemy import select, func
from sqlalchemy import case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.engine import Row

from movies.models import Movie, Genre, MoviesGenresModel, MovieLike


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
        return result.unique().scalar_one_or_none()

    async def get_movie_basic(self, movie_id: int) -> Optional[Movie]:
        result = await self.db.execute(
            select(Movie).where(Movie.id == movie_id)
        )
        return result.unique().scalar_one_or_none()

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
