import json
import asyncio
from typing import Any, Dict, List

import aiofiles
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from logger_config import setup_logging, get_logger
from config import get_settings
from database import get_db_contextmanager

from auth.models import UserGroup, UserGroupEnum
from movies.models import (
    Movie,
    Certification,
    Genre,
    Star,
    Director,
    MoviesGenresModel,
    MoviesStarsModel,
    MoviesDirectorsModel,
)

from seeding.generate_json import JsonDataGenerator

log = get_logger()


class InitialDatabaseSeeder:
    def __init__(self, db_session: AsyncSession, settings: Any):
        self.db = db_session
        self.paths = {
            "certifications": settings.CERT_JSON_PATH,
            "genres": settings.GENRE_JSON_PATH,
            "stars": settings.STARS_JSON_PATH,
            "directors": settings.DIRECTORS_JSON_PATH,
            "movies": settings.MOVIE_JSON_PATH,
        }

    async def _load_json(self, key: str) -> List[Dict[str, Any]]:
        path = self.paths[key]
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            return json.loads(await f.read())

    async def _insert_unique_by_name(
        self,
        model,
        items: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Inserts items into the database if they don't already exist.
        Returns a dictionary mapping item names to their IDs in the database.
        """
        
        if not items:
            return {}

        names = [item["name"] for item in items]

        stmt = select(model).where(model.name.in_(names))
        result = await self.db.execute(stmt)
        existing = {row.name: row.id for row in result.scalars().all()}

        to_insert = [item for item in items if item["name"] not in existing]

        if to_insert:
            await self.db.execute(insert(model), to_insert)
            await self.db.flush()
            result = await self.db.execute(stmt)
            existing = {row.name: row.id for row in result.scalars().all()}

        return existing

    async def _insert_movies(
        self,
        movies: List[Dict[str, Any]],
        cert_map: Dict[str, int]
    ) -> Dict[str, int]:
        if not movies:
            return {}

        for m in movies:
            cert_name = m["certification_name"]
            m["certification_id"] = cert_map[cert_name]
            del m["certification_name"]

        names = [m["name"] for m in movies]

        stmt = select(Movie).where(Movie.name.in_(names))
        result = await self.db.execute(stmt)
        existing = {row.name: row.id for row in result.scalars().all()}

        to_insert = [m for m in movies if m["name"] not in existing]

        if to_insert:
            await self.db.execute(insert(Movie), to_insert)
            await self.db.flush()
            result = await self.db.execute(stmt)
            existing = {row.name: row.id for row in result.scalars().all()}

        return existing

    async def _seed_associations(
        self,
        movie_map: Dict[str, int],
        genre_map: Dict[str, int],
        star_map: Dict[str, int],
        director_map: Dict[str, int],
    ) -> None:
        import random

        movie_ids = list(movie_map.values())
        genre_ids = list(genre_map.values())
        star_ids = list(star_map.values())
        director_ids = list(director_map.values())

        movie_genres: List[Dict[str, int]] = []
        movie_stars: List[Dict[str, int]] = []
        movie_directors: List[Dict[str, int]] = []

        for m_id in movie_ids:
            if genre_ids:
                for g_id in random.sample(genre_ids, k=min(3, len(genre_ids))):
                    movie_genres.append({"movie_id": m_id, "genre_id": g_id})

            if star_ids:
                for s_id in random.sample(star_ids, k=min(5, len(star_ids))):
                    movie_stars.append({"movie_id": m_id, "star_id": s_id})

            if director_ids:
                d_id = random.choice(director_ids)
                movie_directors.append({"movie_id": m_id, "director_id": d_id})

        if movie_genres:
            await self.db.execute(insert(MoviesGenresModel), movie_genres)
        if movie_stars:
            await self.db.execute(insert(MoviesStarsModel), movie_stars)
        if movie_directors:
            await self.db.execute(
                insert(MoviesDirectorsModel), movie_directors
            )

    async def _seed_user_groups(self) -> None:
        """
        Seeds the UserGroup table with the following groups:
            - USER
            - MODERATOR
            - ADMIN

        If any of the groups already exist, they are skipped.
        """
        groups = [
            {"name": UserGroupEnum.USER},
            {"name": UserGroupEnum.MODERATOR},
            {"name": UserGroupEnum.ADMIN},
        ]

        stmt = (
            select(UserGroup)
            .where(UserGroup.name.in_(
                    [g["name"] for g in groups]
                )
            )
        )
        result = await self.db.execute(stmt)
        existing = {row.name for row in result.scalars().all()}

        to_insert = [g for g in groups if g["name"] not in existing]

        if to_insert:
            await self.db.execute(insert(UserGroup), to_insert)
            await self.db.flush()

    async def seed(self) -> None:
        log.info("🔃 Starting database seeding...")

        # 1. Seed user groups
        await self._seed_user_groups()

        # 2. Load JSON data
        certs = await self._load_json("certifications")
        genres = await self._load_json("genres")
        stars = await self._load_json("stars")
        dirs = await self._load_json("directors")
        movies = await self._load_json("movies")

        # 3. Insert base tables
        cert_map = await self._insert_unique_by_name(Certification, certs)
        genre_map = await self._insert_unique_by_name(Genre, genres)
        star_map = await self._insert_unique_by_name(Star, stars)
        director_map = await self._insert_unique_by_name(Director, dirs)

        # 4. Insert movies
        movie_map = await self._insert_movies(movies, cert_map)

        # 5. Insert associations
        await self._seed_associations(movie_map, genre_map, star_map, director_map)

        await self.db.commit()
        log.info("✅ Database seeding completed successfully.")


async def main() -> None:
    setup_logging()
    settings = get_settings()

    try:
        async with get_db_contextmanager() as db:
            generator = JsonDataGenerator(
                certs_json=settings.CERT_JSON_PATH,
                movie_json=settings.MOVIE_JSON_PATH,
                genres_json=settings.GENRE_JSON_PATH,
                stars_json=settings.STARS_JSON_PATH,
                dirs_json=settings.DIRECTORS_JSON_PATH,
            )

            await generator.ensure_json_files_exist()

            seeder = InitialDatabaseSeeder(db, settings)
            await seeder.seed()
    except Exception as e:
        log.error("❌ Database seeding failed: %s", e)
        raise


if __name__ == "__main__":
    asyncio.run(main())
