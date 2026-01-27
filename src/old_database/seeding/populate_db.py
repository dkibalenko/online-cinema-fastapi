import json
import os
from pathlib import Path
import asyncio
import math
import csv
import random
from typing import List, Dict, Tuple, Any, AsyncGenerator, Type
from decimal import Decimal
import uuid

import pandas as pd
from sqlalchemy import insert, select, func, Table
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from tqdm import tqdm
import aiofiles

from logger_config import setup_logging, get_logger
from config import get_settings
from database import (
    Base,
    Movie,
    Certification,
    Genre,
    Star,
    Director,
    MoviesGenresModel,
    MoviesStarsModel,
    MoviesDirectorsModel,
    get_db_contextmanager
)
from database.seeding.generate_json import JsonDataGenerator


# grab the object. it has no handlers yet
log = get_logger()


class MovieDatabaseSeeder:
    """
    A class responsible for seeding the database from a JSON files using 
    asynchronous SQLAlchemy.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        settings: Any
    ):
        self._paths = {
            "certifications": settings.CERT_JSON_PATH,
            "genres": settings.GENRE_JSON_PATH,
            "stars": settings.STARS_JSON_PATH,
            "directors": settings.DIRECTORS_JSON_PATH,
            "movies": settings.MOVIE_JSON_PATH
        }
        self._db_session = db_session

    async def is_db_populated(self) -> bool:
        """
        Checks if the database has been populated by checking if there is
        at least one movie.
        
        Returns:
            bool: True if the database has been populated, False otherwise.
        """
        result = await self._db_session.execute(select(Movie).limit(1))
        return result.scalars().first() is not None
    
    async def _load_json(self, key: str) -> List[Dict[str, Any]]:
        """Reads and returns data from a JSON file."""
        file_path = self._paths.get(key)
        if not file_path or not Path(file_path).exists():
            log.warning(f"File for {key} not found at {file_path}")
            return []

        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content)

    async def _bulk_insert_ignore_duplicates(
        self,
        model: Type[Base],
        data: List[Dict[str, Any]]
    ) -> List[int]:
        """
        Inserts data into the DB. Skips if ID already exists
        (simple deduplication).
        Returns a list of IDs present in the DB (both new and existing).
        """
        if not data:
            return []

        table_name = model.__tablename__
        ids_to_insert = [item["id"] for item in data]
        
        # 1. Check existing IDs
        stmt = select(model.id).where(model.id.in_(ids_to_insert))
        result = await self._db_session.execute(stmt)
        existing_ids = set(result.scalars().all())

        # 2. Filter data
        new_records = [item for item in data if item["id"] not in existing_ids]

        # 3. Insert new
        if new_records:
            log.info(
                f"Inserting {len(new_records)} new records into "
                f"'{table_name}'...")
            # We use core insert to allow setting explicit IDs
            await self._db_session.execute(insert(model), new_records)
            await self._db_session.flush() # Flush to ensure they exist for foreign keys
        
        return ids_to_insert
    
    async def _seed_associations(
        self,
        movie_ids: List[int],
        ref_ids: Dict[str, List[int]]
    ) -> None:
        log.info("Synthesizing and seeding associations...")

        movie_genres = []
        movie_stars = []
        movie_directors = []

        for m_id in movie_ids:
            # Randomly assign 1-3 Genres
            if ref_ids["genres"]:
                selected_genres = random.sample(ref_ids["genres"], k=min(len(ref_ids["genres"]), random.randint(1, 3)))
                for g_id in selected_genres:
                    movie_genres.append({"movie_id": m_id, "genre_id": g_id})

            # Randomly assign 2-5 Stars
            if ref_ids["stars"]:
                selected_stars = random.sample(ref_ids["stars"], k=min(len(ref_ids["stars"]), random.randint(2, 5)))
                for s_id in selected_stars:
                    movie_stars.append({"movie_id": m_id, "star_id": s_id})

            # Randomly assign 1 Director
            if ref_ids["directors"]:
                selected_director = random.choice(ref_ids["directors"])
                movie_directors.append({"movie_id": m_id, "director_id": selected_director})

        # Bulk insert associations (using explicit Table objects)
        if movie_genres:
            await self._db_session.execute(insert(MoviesGenresModel).values(movie_genres))
        if movie_stars:
            await self._db_session.execute(insert(MoviesStarsModel).values(movie_stars))
        if movie_directors:
            await self._db_session.execute(insert(MoviesDirectorsModel).values(movie_directors))

    async def seed(self) -> None:
        try:
            # 1. Load Data from JSONs
            certs_data = await self._load_json("certifications")
            genres_data = await self._load_json("genres")
            stars_data = await self._load_json("stars")
            dirs_data = await self._load_json("directors")
            movies_data = await self._load_json("movies")

            # 2. Insert Reference Data (Independent Tables)
            log.info("Seeding Reference Data...")
            await self._bulk_insert_ignore_duplicates(Certification, certs_data)
            genre_ids = await self._bulk_insert_ignore_duplicates(Genre, genres_data)
            star_ids = await self._bulk_insert_ignore_duplicates(Star, stars_data)
            dir_ids = await self._bulk_insert_ignore_duplicates(Director, dirs_data)

            # 3. Insert Movies (Dependent Table)
            log.info("Seeding Movies...")
            movie_ids = await self._bulk_insert_ignore_duplicates(Movie, movies_data)

            # 4. Insert Associations (Derived/Synthesized)
            # generate M2M links, since JSONs didn't have
            ref_ids = {
                "genres": genre_ids,
                "stars": star_ids,
                "directors": dir_ids
            }
            await self._seed_associations(movie_ids, ref_ids)

            # 5. Commit
            await self._db_session.commit()
            log.info("✅ Seeding completed successfully.")

        except IntegrityError as e:
            log.error(f"Integrity Error during seeding: {e}")
            await self._db_session.rollback()
            raise
        except SQLAlchemyError as e:
            log.error(f"Database Error: {e}")
            await self._db_session.rollback()
            raise
        except Exception as e:
            log.error(f"Unexpected Error: {e}")
            await self._db_session.rollback()
            raise


async def main() -> None:
    """
    Entry point. Checks database state and runs seeder if empty.
    """
    log.info("Running database seeder script...")
    settings = get_settings()

    async with get_db_contextmanager() as db_session:
        # 1. Generate JSON data if missing
        log.info("Checking/Generating JSON source files...")
        json_gen = JsonDataGenerator(
            certs_json=settings.CERT_JSON_PATH,
            movie_json=settings.MOVIE_JSON_PATH,
            genres_json=settings.GENRE_JSON_PATH,
            stars_json=settings.STARS_JSON_PATH,
            dirs_json=settings.DIRECTORS_JSON_PATH
        )
        # This creates files if they don't exist
        await json_gen.ensure_json_files_exist(count=50)

        # 2. Seed Database
        seeder = MovieDatabaseSeeder(db_session, settings)

        if not await seeder.is_db_populated():
            log.info("Database is empty. Starting seeding process...")
            try:
                await seeder.seed()
                log.info("✅ Database seeding completed successfully.")
            except Exception as e:
                log.error(f"⛔Failed to seed the database: {e}")
        else:
            log.info("Database is already populated. Skipping seeding.")

    log.info("Database saver script completed.")


if __name__ == "__main__":
    import sys
    from pathlib import Path
    # loads config.json & attaches handlers (File/Console) and formatters to existing object
    setup_logging()

    # add project root to path for standalone execution if needed
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    asyncio.run(main())
