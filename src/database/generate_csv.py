import os
import csv
import random
import uuid
from decimal import Decimal

from main import log


NUM_MOVIES = 100
CERTIFICATIONS_LIST = ["G", "PG", "PG-13", "R", "NC-17", "Unrated"]
PRICES = [Decimal("4.99"), Decimal("9.99"), Decimal("14.99"), Decimal("19.99")]


def generate_certifications(file_path: str) -> dict:
    """Creates the certifications.csv file."""

    log.info(f"Generating {file_path}...")

    cert_ids = {}

    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "name"])  # Write header

        # Write rows
        for id_, name in enumerate(CERTIFICATIONS_LIST, 1):
            writer.writerow([id_, name])
            cert_ids[name] = id_

    log.info(f"✅ Successfully created {file_path}.")

    return cert_ids


def generate_movies(file_path: str, cert_ids: dict) -> None:
    """Creates the movies.csv file."""

    log.info(f"Generating {file_path}...")

    cert_id_list = list(cert_ids.values())

    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "id", "uu_id", "name", "year", "time", "imdb", "votes",
                "meta_score", "gross", "description", "price",
                "certification_id"
            ]
        )

        for id_ in range(1, NUM_MOVIES + 1):
            movie_name = f"Fake Movie Title {id_}"
            meta_score = (
                random.randint(30, 99)
                if random.random() > 0.2 else ""
            )
            gross = (
                random.randint(1_000_000, 500_000_000)
                if random.random() > 0.2 else ""
            )
            
            writer.writerow(
                [
                    id_, str(uuid.uuid4()), movie_name,
                    random.randint(1980, 2025), random.randint(80, 180),
                    round(random.uniform(4.0, 9.2), 1),
                    random.randint(10000, 1000000), meta_score, gross,
                    f"A description for '{movie_name}'.",
                    random.choice(PRICES), random.choice(cert_id_list)
                ]
            )

    log.info(f"✅ Successfully created {file_path}.")


def ensure_csv_files_exist(cert_path: str, movie_path: str) -> None:
    """Checks if CSV files exist, generating them if not."""

    cert_ids = {}

    if not os.path.exists(cert_path):
        log.warning(f"{cert_path} not found. Generating new file.")

        cert_ids = generate_certifications(cert_path)
    else:
        log.info(f"Found {cert_path}.")

        # Read existing IDs
        with open(cert_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                cert_ids[row["name"]] = int(row["id"])

    if not os.path.exists(movie_path):
        log.warning(f"{movie_path} not found. Generating new file.")

        if not cert_ids: # Should be populated from block above
             log.error("Cannot generate movies, certification IDs unknown.")
             return

        generate_movies(movie_path, cert_ids)
    else:
        log.info(f"Found {movie_path}.")
