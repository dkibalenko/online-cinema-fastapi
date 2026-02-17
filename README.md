# Online Cinema

An online cinema is a digital platform that allows users to select, watch, and purchase access to movies and other video materials via the internet.

## 🔐 Authentication & User Management

The project uses a clean domain‑based architecture with separate apps:

- `auth/` — authentication, tokens, login, registration
- `users/` — user identity, profiles, roles (RBAC)

This separation keeps the codebase maintainable and avoids circular imports.

### 📁 Directory Structure
```
src/
  __init__.py
  auth/
    __init__.py
    router.py
    service.py
    repository.py
    dependencies.py
    models.py
  users/
    __init__.py
    router.py
    service.py
    repository.py
    dependencies.py
    models.py
    enums.py
    validators.py
    utils.py
```
### 🔐 Auth App
The auth app handles:
- User registration
- Email activation
- Login
- Refresh tokens
- Logout
- Password reset (request + complete)
- Password change
- Token validation
- Email notifications via Celery

#### Token Models

All token models inherit from a shared TokenBaseModel:
- `ActivationToken`
- `PasswordResetToken`
- `RefreshToken`

They are stored in a single module:
```
auth/models.py
```
This keeps the authentication domain cohesive and avoids fragmentation.

#### JWT Authentication

The project uses:
- Access tokens (short‑lived)
- Refresh tokens (stored in DB)
- Role‑based access control (RBAC)

`get_current_user` decodes the access token and loads the user from the database.

### 👤 Users App
The users app manages:
- User entity
- User groups (RBAC)
- User profiles
- Profile creation
- Profile retrieval
- `/users/me` endpoint

#### User Models
All user‑related models live in one file:
```
users/models.py
```
This includes:
- `User`
- `UserGroup`
- `UserProfile`

Enums are stored separately:
```
users/enums.py
```

#### User Profiles
Users can create a profile with:
- First name
- Last name
- Gender
- Birth date
- Info
- Avatar (uploaded to S3)

Admins can create profiles for other users.

#### `/users/me` Endpoint
Authenticated users can retrieve their own profile:
```
GET /api/v1/cinema/users/me/
```
Returns:
- Profile data
- Avatar URL
- User metadata

---

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

## Movies App

Structure:
```
movies/
│
├── router.py
├── dependencies.py
├── service.py
├── repository.py
├── exceptions.py
├── utils.py
├── filters.py
├── schemas.py
└── models.py
```
