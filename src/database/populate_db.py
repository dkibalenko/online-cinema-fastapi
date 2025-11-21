import csv
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from tqdm.asyncio import tqdm

from main import log
from config import get_settings
from database import (
    Movie,
    Certification,
    get_db_contextmanager,
    init_db,
    ensure_csv_files_exist
)


class DatabasePopulator:
    """Class to populate the database from CSV files."""

    def __init__(
            self,
            cert_csv_path: str,
            movie_csv_path: str,
            db_session: AsyncSession
        ):
        self._cert_csv_path = cert_csv_path
        self._movie_csv_path = movie_csv_path
        self._db_session = db_session

    async def is_db_populated(self) -> bool:
        """Check if the movie database already contains records."""

        stmt = select(func.count()).select_from(Movie)
        result = await self._db_session.execute(stmt)
        total_count = result.scalar_one()
        return total_count > 0

    async def _seed_certifications(self):
        """Seeds the 'certifications' table."""

        log.info("Seeding certifications...")

        with open(self._cert_csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in tqdm(list(reader), desc="Seeding Certifications"):
                cert = Certification(
                    id=int(row["id"]),
                    name=row["name"]
                )
                self._db_session.add(cert)

        log.info("Certifications added to session.")

    async def _seed_movies(self):
        """Seeds the 'movies' table."""

        log.info("Seeding movies...")

        with open(self._movie_csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in tqdm(list(reader), desc="Seeding Movies"):
                movie = Movie(
                    id=int(row["id"]),
                    uu_id=row["uu_id"], # Already a string
                    name=row["name"],
                    year=int(row["year"]),
                    time=int(row["time"]),
                    imdb=float(row["imdb"]),
                    votes=int(row["votes"]),
                    meta_score=self._convert_type(row["meta_score"], float),
                    gross=self._convert_type(row["gross"], Decimal),
                    description=row["description"],
                    price=self._convert_type(
                        row["price"],
                        Decimal,
                        Decimal("0.00")
                    ),
                    certification_id=int(row["certification_id"])
                )
                self._db_session.add(movie)

        log.info("Movies added to session.")

    async def seed_database(self) -> None:
        """
        Seeds all tables from CSV files in the correct order.
        """

        await self._seed_certifications()
        await self._seed_movies()

        log.info("Database seeding added to session.")

    @staticmethod
    def _convert_type(val, target_type, default=None):
        if val is None or val == "":
            return default
        try:
            return target_type(val)
        except (ValueError, TypeError):
            return default


async def main() -> None:
    """Entry point for the database seeding process."""

    settings = get_settings()
    
    cert_path = settings.CERT_CSV_PATH
    movie_path = settings.MOVIE_CSV_PATH

    # 1. Ensure CSVs exist, generate them if they don't
    # This must be run *before* init_db in case paths are relative
    ensure_csv_files_exist(cert_path, movie_path)

    # 2. Initialize database (create tables)
    log.info("Initializing database tables...")
    await init_db()
    log.info("Database initialized.")

    # 3. Get DB session and run populator
    try:
        async with get_db_contextmanager() as db_session:
            # db_session is open, but NO transaction is active yet.
            populator = DatabasePopulator(cert_path, movie_path, db_session)
            # ONE explicit transaction
            async with db_session.begin():
                if not await populator.is_db_populated():
                    log.info("Database is empty. Starting seeding process...")
                    await populator.seed_database()
                    log.info("✅ Database seeding committed successfully.")
                else:
                    log.info("Database is already populated. Skip seeding.")

    except IntegrityError as e:
        log.error(f"Integrity Error: {e}. Data might be misaligned.")
    except SQLAlchemyError as e:
        log.error(f"A SQLAlchemy error occurred: {e}")
    except Exception as e:
        log.error(f"❌ Failed to seed the database: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
