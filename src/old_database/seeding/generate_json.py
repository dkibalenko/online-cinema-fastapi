import os
import json
from pathlib import Path
import random
from typing import Any, Callable, Dict, List, Optional
import uuid
from decimal import Decimal
import asyncio

import httpx
import aiofiles

from logger_config import get_logger

log = get_logger()


CERTIFICATIONS_LIST = ["G", "PG", "PG-13", "R", "NC-17"]
PRICES = [4.99, 9.99, 14.99, 19.99]
MOVIES_COUNT = 100
CERT_COUNT = 5
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
    "Western"
]


class JsonDataGenerator:
    def __init__(
        self,
        certs_json: str,
        movie_json: str,
        genres_json: str,
        stars_json: str,
        dirs_json: str
    ):
        self._certs_json = certs_json
        self._movie_json = movie_json
        self._genres_json = genres_json
        self._stars_json = stars_json
        self._dirs_json = dirs_json

    async def _generate_certifications(self) -> List[int]:
        """Creates the certifications.json file and returns a list of IDs."""

        log.info(f"Generating certifications file: {self._certs_json}")
        Path(self._certs_json).parent.mkdir(parents=True, exist_ok=True)

        certifications: List[Dict[str, Any]] = []
        cert_ids: List[int] = []

        for cert_id, name in enumerate(CERTIFICATIONS_LIST, start=1):
            certificate = {
                "id": cert_id,
                "name": name
            }
            certifications.append(certificate)
            
            cert_ids.append(cert_id)

        try:
            async with aiofiles.open(self._certs_json, "w", encoding="utf-8") as f:
                await f.write(json.dumps(certifications, indent=2, ensure_ascii=False))
        except (TypeError, OSError) as e:
            log.error(
                f"Failed to write certifications to {self._certs_json}: {e}"
            )
            raise

        log.info(
            f"✅ Successfully created {self._certs_json} with "
            f"{len(certifications)} items."
        )

        return cert_ids

    async def _generate_movies(self, cert_ids: list) -> List[int]:

        log.info(f"Generating movies file: {self._movie_json}")

        if not cert_ids:
            raise ValueError("cert_ids must be a non-empty list")

        Path(self._movie_json).parent.mkdir(parents=True, exist_ok=True)

        movies: List[Dict[str, Any]] = []
        movie_ids: List[int] = []

        for movie_id in range(1, MOVIES_COUNT + 1):
            name = f"Fake Movie Title {movie_id}"
            meta_score: Optional[int] = (
                random.randint(30, 99)
                if random.random() > 0.2 else None  # ? ""
            )
            gross_value: Optional[int] = (
                random.randint(1_000_000, 500_000_000)
                if random.random() > 0.2 else None  # ? ""
            )

            movie: Dict[str, Any] = {
                    "id": movie_id,
                    "name": name,
                    "year": random.randint(1980, 2025),
                    "time": random.randint(80, 180),
                    "imdb": round(random.uniform(4.0, 9.2), 1),
                    "votes": random.randint(10000, 1000000),
                    "meta_score": meta_score,
                    "gross": float(gross_value) if gross_value is not None else None,
                    "description": f"A description for '{name}'.",
                    "price": float(random.choice(PRICES)),
                    "certification_id": int(random.choice(cert_ids))
                }
            movies.append(movie)
            movie_ids.append(movie_id)

        try:
            async with aiofiles.open(self._movie_json, "w", encoding="utf-8") as f:
                await f.write(json.dumps(movies, indent=2, ensure_ascii=False))
        except (TypeError, OSError) as e:
            log.error(f"Failed to write movies to {self._movie_json}: {e}")
            raise

        log.info(
            f"✅ Successfully created {self._movie_json} with "
            f"{len(movies)} movies."
        )

        return movie_ids

    @staticmethod
    async def _fetch_random_names(count: int = 50) -> List[str]:
        """
        Fetch random names from https://randomuser.me/api/

        :param count: Number of names to fetch
        :return: List of full names
        """
        names: List[str] = []
        names_fetched = 0

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                while names_fetched < count:
                    response = await client.get("https://randomuser.me/api/")
                    response.raise_for_status()

                    data = response.json()
                    
                    if not data.get("results") or not isinstance(data["results"], list) or not data["results"]:
                        log.warning(
                            "Random name API returned an empty or invalid 'results' list. "
                            "Retrying this fetch."
                        )

                        await asyncio.sleep(0.5)
                        continue
                        
                    user = data["results"][0]
                    full_name = (
                        f"{user['name']['first']} {user['name']['last']}"
                    )
                    names.append(full_name)
                    names_fetched += 1

                    await asyncio.sleep(0.1)

            log.info(f"✅Fetched {len(names)} random names from randomuser.me")
            return names

        except httpx.RequestError as e:
            log.error(f"Failed to fetch random names: {e}")
            raise

    async def _generate_genres(self) -> List[int]:
        log.info(
            f"Generating genres.json file: {self._genres_json} and "
            f"return a list of IDs."
        )
        Path(self._genres_json).parent.mkdir(parents=True, exist_ok=True)

        genres: List[Dict[str, Any]] = []
        genre_ids: List[int] = []

        for genre_id, name in enumerate(GENRES, start=1):
            certificate = {
                "id": genre_id,
                "name": name
            }
            genres.append(certificate)
            
            genre_ids.append(genre_id)

        try:
            async with aiofiles.open(self._genres_json, "w", encoding="utf-8") as f:
                await f.write(json.dumps(genres, indent=2, ensure_ascii=False))
        except (TypeError, OSError) as e:
            log.error(f"Failed to write genres to {self._genres_json}: {e}")
            raise

        log.info(
            f"✅ Successfully created {self._genres_json} with "
            f"{len(genres)} items."
        )

        return genre_ids

    async def _generate_names(
        self,
        file_path: str,
        file_name: str,
        count: int = 50
    ) -> List[int]:
        log.info(
            f"Generating {file_name}.json file: {file_path} and return a list of IDs."
        )
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            names = await self._fetch_random_names(count)
        except httpx.RequestError as e:
            log.error(f"Failed to fetch names for {file_name}: {e}")
            raise

        if not names:
            raise ValueError(f"No names fetched for {file_name}")

        name_list = [{"id": i + 1, "name": n} for i, n in enumerate(names)]

        try:
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(name_list, indent=2, ensure_ascii=False))
        except (TypeError, OSError) as e:
            log.error(f"Failed to write {file_name} to {file_path}: {e}")
            raise

        log.info(
            f"✅ Successfully created {file_path} with {len(name_list)} items."
        )

        return [item["id"] for item in name_list]

    async def _read_json_ids(self, file_path: str) -> List[int]:
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
            
            # --- Robustness Check: If content is empty/whitespace, it's corrupt ---
            if not content.strip():
                 # Raise a JSONDecodeError just like the original issue, but provide more info
                 raise json.JSONDecodeError("File content is empty or corrupt.", content, 0)
            
            items = json.loads(content)
            
        except (json.JSONDecodeError, OSError) as e:
            log.error(f"Failed to read IDs from {file_path}: {e}")
            raise
            
        if not isinstance(items, list):
            raise ValueError(
                f"Expected list in {file_path}, got {type(items)}"
            )

        ids = [
            item.get("id")
            for item in items 
            if isinstance(item, dict) and "id" in item
        ]

        if not ids:
            raise ValueError(f"No valid IDs found in {file_path}")

        return ids

    async def _ensure_certs_genres_json_exist(self) -> Dict[str, List[int]]:
        data_ids: Dict[str, List[int]] = {}
        
        for path, key, func in [
            (self._certs_json, "cert_ids", self._generate_certifications),
            (self._genres_json, "genre_ids", self._generate_genres)
        ]:
            needs_generation = False
            
            if not os.path.exists(path):
                log.warning(f"{path} not found. Needs generation.")
                needs_generation = True
            else:
                log.info(f"Found {path}. Checking integrity...")
                try:
                    # Attempt to read existing file
                    data_ids[key] = await self._read_json_ids(path)
                    log.info(f"✅ Successfully read existing data from {path}.")
                except (ValueError, OSError, json.JSONDecodeError) as e:
                    # FIX: Catch JSONDecodeError (the original issue) and other file/value errors
                    log.error(
                        f"Failed to read or decode {path}: {e}. "
                        f"File appears corrupt. Deleting and regenerating."
                    )
                    
                    # 1. Attempt to delete the corrupt file
                    try:
                        os.remove(path)
                    except OSError as remove_e:
                        log.error(f"Failed to delete corrupt file {path}: {remove_e}. Re-raising.")
                        raise 
                        
                    needs_generation = True

            if needs_generation:
                log.warning(f"Generating missing or corrupt file: {path}...")
                try:
                    # Re-call the generator function
                    data_ids[key] = await func()
                except (ValueError, OSError) as e:
                    log.error(f"Failed to generate {path}: {e}")
                    raise

        return data_ids

    async def ensure_json_files_exist(self, count: int = 50) -> Dict[str, List]:
        data_ids: Dict[str, List[int]] = {}

        # Phase 1: Handle files with no dependencies (certifications, genres)
        log.info("Phase 1: Generating independent seed files...")
        
        # This function now handles file corruption and regeneration
        data_ids.update(await self._ensure_certs_genres_json_exist())

        # Phase 2: Generate movies (depends on cert_ids)
        log.info("Phase 2: Generating movies seed file...")
        
        if not data_ids.get("cert_ids"):
            raise ValueError("Cannot generate movies: cert_ids is empty")
        
        movie_exists = os.path.exists(self._movie_json)
        needs_movie_generation = False

        if not movie_exists:
            log.warning(f"{self._movie_json} not found. Generating...")
            needs_movie_generation = True
        else:
            log.info(f"Found {self._movie_json}. Checking integrity...")
            try:
                data_ids["movie_ids"] = await self._read_json_ids(self._movie_json)
                log.info(f"✅ Successfully read existing data from {self._movie_json}.")
            except (ValueError, OSError, json.JSONDecodeError) as e:
                log.error(
                    f"Failed to read or decode {self._movie_json}: {e}. "
                    f"File appears corrupt. Deleting and regenerating."
                )
                try:
                    os.remove(self._movie_json)
                except OSError as remove_e:
                    log.error(f"Failed to delete corrupt movie file: {remove_e}. Re-raising.")
                    raise 
                needs_movie_generation = True

        if needs_movie_generation:
            data_ids["movie_ids"] = await self._generate_movies(data_ids["cert_ids"])


        # Phase 3: Generate names from API (stars, directors) — async
        log.info("Phase 3: Generating seed files with random names...")
        
        for path, key, name in [
            (self._stars_json, "stars_ids", "stars"),
            (self._dirs_json, "dirs_ids", "directors")
        ]:
            needs_name_generation = False
            
            if not os.path.exists(path):
                log.warning(f"{path} not found. Needs generation.")
                needs_name_generation = True
            else:
                log.info(f"Found {path}. Checking integrity...")
                try:
                    data_ids[key] = await self._read_json_ids(path)
                    log.info(f"✅ Successfully read existing data from {path}.")
                except (ValueError, OSError, json.JSONDecodeError) as e:
                    log.error(
                        f"Failed to read or decode {path}: {e}. "
                        f"File appears corrupt. Deleting and regenerating."
                    )
                    try:
                        os.remove(path)
                    except OSError as remove_e:
                        log.error(f"Failed to delete corrupt name file: {remove_e}. Re-raising.")
                        raise
                    needs_name_generation = True

            if needs_name_generation:
                log.warning(f"Generating missing or corrupt file: {path}...")
                try:
                    data_ids[key] = await self._generate_names(
                        path, name, count
                    )
                except (ValueError, OSError, httpx.RequestError) as e:
                    log.error(f"Failed to generate {path}: {e}")
                    raise
        
        log.info(f"✅ All seed files ready: {list(data_ids.keys())}")

        return data_ids
