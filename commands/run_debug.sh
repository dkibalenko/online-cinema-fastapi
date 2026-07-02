#!/bin/sh

echo "Starting Uvicorn with debugpy on port 5678..."
python -m debugpy --listen 0.0.0.0:5678 \
    -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000
