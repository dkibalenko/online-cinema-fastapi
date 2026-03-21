#!/bin/sh
set -e

ALEMBIC_CONFIG="/usr/src/alembic.ini"

echo "=== Running Alembic migrations ==="

export PGPASSWORD="$POSTGRES_PASSWORD"

# Check if alembic_version table exists
ALEMBIC_TABLE_EXISTS=$(psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -tAc "SELECT to_regclass('public.alembic_version');")

if [ "$ALEMBIC_TABLE_EXISTS" = "alembic_version" ]; then
    echo "Alembic version table exists. Applying pending migrations..."
    alembic -c "$ALEMBIC_CONFIG" upgrade head

    # if [ "$FORCE_SEED" = "true" ]; then
    #     echo "FORCE_SEED enabled — running database seeder..."
    #     python -m seeding.populate_db
    #     echo "Database seeding completed."
    # else
    #     echo "FORCE_SEED not enabled — skipping seeding."
    # fi

else
    echo "Alembic version table NOT found. Fresh database detected."

    echo "Applying all existing migrations..."
    alembic -c "$ALEMBIC_CONFIG" upgrade head

    echo "Running database seeder..."
    python -m seeding.populate_db
    echo "Database seeding completed."
fi

echo "=== Migration process finished ==="
