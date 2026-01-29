# Online Cinema

An online cinema is a digital platform that allows users to select, watch, and purchase access to movies and other video materials via the internet.

## Database Migrations (Local + Docker)
This project uses Alembic for SQLAlchemy schema migrations.
Migrations are generated locally and applied inside Docker using a dedicated migrator service.

This section explains:
- How migrations work
- How to generate them locally
- How Docker applies them
- Why two Alembic config files exist
- How the project structure is wired

### 🔧 Project Structure (relevant to Alembic)
```
project/
│
├── src/                     # Application code
│   ├── database.py          # SQLAlchemy Base + engine
│   ├── auth/models.py
│   ├── movies/models.py
│   └── ...
│
├── alembic/                 # Alembic migration folder
│   ├── env.py               # Alembic environment
│   ├── script.py.mako
│   └── versions/            # Migration files
│
├── alembic.ini              # Docker Alembic config
├── alembic.local.ini        # Local Alembic config
└── docker-compose.yml
```
### Why Two Alembic Config Files?
- `alembic.local.ini`

Used only on a local machine to generate migrations.
It connects to the local PostgreSQL instance:
```shell
sqlalchemy.url = postgresql://cinema_user:cinema_password@localhost:5432/cinema_db
```

- `alembic.ini`

Used inside Docker by the migrator container.
It connects to the Docker Postgres service:
```shell
sqlalchemy.url = postgresql://cinema_user:cinema_password@<db-servie-name>:5432/cinema_db
```

### Local Migration Workflow
1. Ensure local PostgreSQL is running
2. Generate a migration:

```shell
poetry run alembic -c alembic.local.ini revision --autogenerate -m "message"
```
3. Review the generated file in `alembic/versions/`
4. Commit it to Git

### 🐳 Docker Migration Workflow
Docker uses a dedicated migrator service:
```yml
migrator:
  build: .
  command: ["/bin/bash", "/commands/run_migrations.sh"]
  depends_on:
    db:
      condition: service_healthy
  volumes:
    - ./src:/usr/src/fastapi
    - ./alembic.ini:/usr/src/alembic.ini:ro
    - ./alembic:/usr/src/alembic:ro
  env_file:
    - .env
  environment:
    - PYTHONPATH=/usr/src/fastapi
```
What it does:
- Waits for Postgres to become healthy
- Runs:
```
alembic -c alembic.ini upgrade head
```
- Applies all committed migrations
- Exits

This ensures:
- Migrations run automatically on container startup
- No autogeneration happens inside Docker. Docker should only apply migrations, never create them.
- Database schema is always up‑to‑date