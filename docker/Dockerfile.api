FROM python:3.12.3

# Setting environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=off
ENV ALEMBIC_CONFIG=/usr/src/alembic.ini

# Installing dependencies
RUN apt update && apt install -y \
    gcc \
    libpq-dev \
    netcat-openbsd \
    postgresql-client \
    dos2unix \
    && apt clean

# Install Poetry
RUN python -m pip install --upgrade pip && \
    pip install poetry

# Copy dependency files
COPY ./poetry.lock /usr/src/poetry/poetry.lock
COPY ./pyproject.toml /usr/src/poetry/pyproject.toml

# Copy Alembic config and scripts
COPY ./alembic /usr/src/alembic
COPY ./alembic.ini /usr/src/alembic.ini

# Configure Poetry to avoid creating a virtual environment
RUN poetry config virtualenvs.create false

# Selecting a working directory
WORKDIR /usr/src/poetry

# Install dependencies with Poetry
RUN poetry lock
RUN poetry install --no-root --only main

# Selecting a working directory
WORKDIR /usr/src/fastapi

# Copy the source code
COPY ./src .

# Copy commands
COPY ./commands /commands

# Ensure Unix-style line endings for scripts
RUN dos2unix /commands/*.sh

# Add execute bit to commands files
RUN chmod +x /commands/*.sh

# Add a non-root user (runs the worker as your host user inside the container)
RUN adduser --disabled-password --no-create-home cinemauser

# Create logs directory and file, give ownership to cinemauser
RUN mkdir -p /var/log/app && \
    touch /var/log/app/app.log && \
    chown -R cinemauser:cinemauser /var/log/app

# Switch to non-root user for runtime
USER cinemauser

