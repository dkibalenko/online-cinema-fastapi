#!/bin/sh

echo "Starting Uvicorn server..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /usr/src/fastapi
# uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4  # production load testing
