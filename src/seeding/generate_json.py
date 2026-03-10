import asyncio
import json
import random
from pathlib import Path
from typing import Any

import aiofiles
import httpx

from logger_config import get_logger

log = get_logger()

CERTIFICATIONS_LIST = ["G", "PG", "PG-13", "R", "NC-17"]
PRICES = [4.99, 9.99, 14.99, 19.99]
MOVIES_COUNT = 100
GENRES = [
    "Action",
    "Adventure",
    "Animation",
    "Biography",
    "Comedy",
    "Crime",
    "Documentary",
    "Drama",
    "Family",
    "Fantasy",
    "Film-Noir",
    "History",
    "Horror",
    "Music",
    "Musical",
    "Mystery",
    "Romance",
    "Science Fiction",
    "Sport",
    "Thriller",
    "War",
    "Western",
]

FALLBACK_NAMES = [
    "John Smith",
    "Jane Doe",
    "Alice Johnson",
    "Bob Williams",
    "Charlie Brown",
    "Diana Prince",
    "Bruce Wayne",
    "Clark Kent",
    "Peter Parker",
    "Natasha Romanoff",
]


class JsonDataGenerator:
    def __init__(
        self,
        certs_json: str,
        movie_json: str,
        genres_json: str,
        stars_json: str,
        dirs_json: str,
    ):
        self._certs_json = certs_json
        self._movie_json = movie_json
        self._genres_json = genres_json
        self._stars_json = stars_json
        self._dirs_json = dirs_json

    async def _generate_certifications(self) -> None:
        Path(self._certs_json).parent.mkdir(parents=True, exist_ok=True)
        data = [{"name": name} for name in CERTIFICATIONS_LIST]

        async with aiofiles.open(self._certs_json, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False))

        log.info("Generated certifications.json with %d items.", len(data))

    async def _generate_genres(self) -> None:
        Path(self._genres_json).parent.mkdir(parents=True, exist_ok=True)
        data = [{"name": name} for name in GENRES]

        async with aiofiles.open(
            self._genres_json, "w", encoding="utf-8"
        ) as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False))

        log.info("Generated genres.json with %d items.", len(data))

    async def _generate_movies(self) -> None:
        Path(self._movie_json).parent.mkdir(parents=True, exist_ok=True)

        movies: list[dict[str, Any]] = []
        for _ in range(MOVIES_COUNT):
            name = f"Fake Movie {random.randint(1000, 9999)}"
            meta_score = (
                random.randint(30, 99) if random.random() > 0.2 else None
            )
            gross_value = (
                random.randint(1_000_000, 500_000_000)
                if random.random() > 0.2
                else None
            )

            movie = {
                "name": name,
                "year": random.randint(1980, 2025),
                "time": random.randint(80, 180),
                "imdb": round(random.uniform(4.0, 9.2), 1),
                "votes": random.randint(10000, 1000000),
                "meta_score": meta_score,
                "gross": float(gross_value) if gross_value else None,
                "description": f"A description for '{name}'.",
                "price": float(random.choice(PRICES)),
                "certification_name": random.choice(CERTIFICATIONS_LIST),
            }
            movies.append(movie)

        async with aiofiles.open(self._movie_json, "w", encoding="utf-8") as f:
            await f.write(json.dumps(movies, indent=2, ensure_ascii=False))

        log.info("Generated movies.json with %d items.", len(movies))

    async def _generate_names(
        self, file_path: str, label: str, count: int = 50
    ) -> None:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        names: list[dict[str, str]] = []
        max_attempts = count * 3
        attempts = 0

        async with httpx.AsyncClient(timeout=10.0) as client:
            while len(names) < count and attempts < max_attempts:
                attempts += 1
                try:
                    resp = await client.get("https://randomuser.me/api/")
                    resp.raise_for_status()
                    data = resp.json()
                    results = data.get("results") or []
                    if not results:
                        log.warning(
                            "randomuser.me returned empty results, retrying..."
                        )
                        await asyncio.sleep(0.2)
                        continue
                    user = results[0]
                    full_name = (
                        f"{user['name']['first']} {user['name']['last']}"
                    )
                    names.append({"name": full_name})
                    await asyncio.sleep(0.1)
                except httpx.RequestError as e:
                    log.error("Error calling randomuser.me: %s", e)
                    await asyncio.sleep(0.5)

        if len(names) < count:
            log.warning(
                (
                    "Could not fetch enough names from API (%d/%d)."
                    "Using fallback names."
                ),
                len(names),
                count,
            )
            while len(names) < count:
                names.append({"name": random.choice(FALLBACK_NAMES)})

        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(names, indent=2, ensure_ascii=False))

        log.info("Generated %s.json with %d items.", label, len(names))

    async def ensure_json_files_exist(self, count: int = 50) -> None:
        """Ensures all JSON seed files exist, generating them if they don't.

        This method is idempotent and can be safely called multiple times.

        Args:
            count (int, optional): The number of names to generate for
                stars and directors. Defaults to 50.

        Returns:
            None
        """
        if not Path(self._certs_json).exists():
            await self._generate_certifications()

        if not Path(self._genres_json).exists():
            await self._generate_genres()

        if not Path(self._movie_json).exists():
            await self._generate_movies()

        if not Path(self._stars_json).exists():
            await self._generate_names(self._stars_json, "stars", count)

        if not Path(self._dirs_json).exists():
            await self._generate_names(self._dirs_json, "directors", count)

        log.info("✅ All JSON seed files are ready.")
