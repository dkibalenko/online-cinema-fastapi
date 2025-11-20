#!/bin/sh

echo "Running database saver script..."
python -m database.populate_db
echo "Database saver script completed."

echo "Starting Uvicorn server..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /usr/src/fastapi
