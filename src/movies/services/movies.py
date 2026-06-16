import hashlib
import json

from fastapi import HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.exc import IntegrityError

from cache.service import CacheService
from logger_config import get_logger
from movies.filters import build_movie_filter_query
from movies.models import Certification, Director, Genre, Movie, Star
from movies.repositories import MovieRepository
from movies.schemas import (
    GenreWithCountSchema,
    MovieCreateSchema,
    MovieDetailSchema,
    MovieFilterParams,
    MovieSortParams,
    MovieUpdateSchema,
)
from movies.services.cache import MovieCacheInvalidationService
from movies.utils import get_or_create_related

log = get_logger()


class MovieService:
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

        filter_data = filter_query.model_dump()
        sort_data = sort_query.model_dump()

        raw_key = json.dumps(
            {"filters": filter_data, "sort": sort_data},
            sort_keys=True,
        )
        hashed = hashlib.md5(raw_key.encode()).hexdigest()
        cache_key = f"movies:list:{user_id}:{hashed}"

        if self.enable_cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return Page(**cached)

        filtered_query = build_movie_filter_query(filter_query, sort_query)
        page = await paginate(self.repo.db, filtered_query)

        favorite_ids = await self.repo.get_favorite_movie_ids(user_id)
        for movie in page.items:
            movie.is_favorite = movie.id in favorite_ids

        if self.enable_cache:
            await self.cache.set(cache_key, page.model_dump(), ttl=60)

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

        if self.enable_cache:
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

        if self.enable_cache:
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
            certification = (
                await get_or_create_related(
                    Certification, [data.certification], self.repo.db
                )
            )[0]
            genres = await get_or_create_related(
                Genre, data.genres, self.repo.db
            )
            stars = await get_or_create_related(Star, data.stars, self.repo.db)
            directors = await get_or_create_related(
                Director, data.directors, self.repo.db
            )

            movie_dict = data.model_dump(
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
            await self.repo.refresh_with_relations(movie)

            log.info(f"Movie created | movie_id={movie.id}")
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

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            log.warning(f"No fields provided for update | movie_id={movie_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update.",
            )

        for field, value in update_data.items():
            setattr(movie, field, value)

        try:
            await self.repo.commit()
            await self.repo.refresh_with_relations(movie)

            log.info(f"Movie updated | movie_id={movie.id}")
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
            cache_key, [r.model_dump() for r in result], ttl=3600
        )
        return result
