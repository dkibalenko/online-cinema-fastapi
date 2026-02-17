from typing import Any, Optional, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.engine import Row

from movies.models import Movie, Genre, MoviesGenresModel


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
