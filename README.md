# Online Cinema

This project is an actively developed, production‑grade RESTful API built with FastAPI, SQLAlchemy 2.0, Celery, Redis, PostgreSQL, Docker, MinIO, MailHog and many other tools.  
It already includes a complete authentication system, user management, movie catalog with genres/stars/directors, likes, ratings, email workflows, and a fully containerized multi‑service architecture.

I continue expanding the system daily — CI/CD, deployment, and automated test coverage are next on the roadmap. The goal is to **demonstrate real backend engineering practices**, not just CRUD endpoints.

An online cinema is a digital platform that allows users to select, watch, and purchase access to movies and other video materials via the internet.


## ⭐ Authentication System
The authentication subsystem provides a complete, secure, and production‑ready identity flow for the Online Cinema platform. It includes user onboarding, JWT‑based authentication, role‑based access control, and asynchronous email notifications.

### Features Overview
The Auth app handles:
- User registration
- Email activation (activation token + Celery email)
- Login (JWT access + refresh tokens)
- Refresh token rotation
- Logout (refresh token invalidation)
- Password reset (request + complete)
- Password change
- Token validation
- Email notifications via Celery
- Role‑based access control (RBAC)

All flows are designed to be secure, scalable, and easy to integrate with other services.

---

### Token Models

All token types inherit from a shared `TokenBaseModel`, ensuring consistency and reducing duplication.

Token types include:
- `ActivationToken` — sent during registration
- `PasswordResetToken` — used for password recovery
- `RefreshToken` — stored in DB for session management

They are stored in a single module:
```
auth/models.py
```
This keeps the authentication domain cohesive and avoids fragmentation.

---

### JWT Authentication
The system uses a two‑token strategy:
#### Access Token
- Short‑lived
- Encodes user ID, token type, and expiration
- Used for authenticating API requests
- Verified using get_current_user

#### Refresh Token
- Long‑lived
- Stored in the database
- Rotated on each refresh
- Invalidated on logout
- Prevents replay attacks

Token Payload Example:
```json
{
  "user_id": 1,
  "type": "access",
  "exp": 1771927955
}
```

---

### Authentication Flow
#### 1. Registration
User submits email + password → receives activation email.

#### 2. Email Activation
User clicks activation link → account becomes active.

#### 3. Login
User receives:
- access_token
- refresh_token

#### 4. Authenticated Requests
Clients send:
```
Authorization: Bearer <access_token>
```
#### 5. Token Refresh
Client exchanges refresh token for new tokens.

#### 6. Logout
Refresh token is deleted from DB.

---

### HTTP Bearer Authentication (Swagger‑Friendly)
The project uses HTTPBearer for token extraction:
```python
from fastapi.security import HTTPBearer

bearer_scheme = HTTPBearer()
```
This provides:
- Clean Swagger UI (“Bearer Token” input)
- No OAuth2 password flow confusion
- Simple extraction of `Authorization: Bearer <token>`

#### `get_current_user` Flow
- Extract token from header
- Decode JWT
- Validate token type
- Load user from DB
- Check activation status
- Return authenticated user

This dependency powers all protected routes.

---

### Role‑Based Access Control (RBAC)
Roles are defined in `UserGroupEnum`:
- ADMIN
- MODERATOR
- USER

Routes can enforce roles using:
```python
@router.post("/movies", dependencies=[Depends(require_role(UserGroupEnum.ADMIN))])
```
The `require_role` dependency ensures only authorized users can access sensitive endpoints.

---

### Email Notifications (Celery)
The Auth app sends emails asynchronously using Celery:
- Activation email
- Password reset email
- Password reset confirmation
- Activation confirmation

SMTP is handled by Mailhog during development.

This keeps the API responsive and avoids blocking I/O.

---

### Auth Architecture Summary
| Component            | Responsibility                        |
| -------------------- | ------------------------------------- |
| **`JWTAuthManager`**   | Encode/decode access & refresh tokens |
| **`AuthRepository`**   | DB operations for users & tokens      |
| **`AuthService`**      | High‑level auth logic                 |
| **`HTTPBearer`**       | Extracts JWT from headers             |
| **`get_current_user`** | Validates token & loads user          |
| **Celery tasks**     | Sends auth‑related emails             |
| **Token models**     | Activation, reset, refresh tokens     |

---

### Testing Authentication
#### Login
```
POST /api/v1/cinema/auth/login
```
#### Use token in Swagger
```
Authorize → Bearer Token → <access_token>
```
#### Refresh token
```
POST /api/v1/cinema/auth/refresh
```
#### Logout
```
POST /api/v1/cinema/auth/logout
```

---

### Summary
The authentication subsystem is:
- Modular
- Secure
- JWT‑based
- Role‑aware
- Asynchronous
- Swagger‑friendly
- Production‑ready

It provides a complete foundation for user identity, session management, and secure access control across the entire platform.


## ⭐ Users App
The Users App provides a complete user management subsystem, including user entities, profiles, RBAC (role‑based access control), and a full administrative console for managing users and permissions. It integrates tightly with the **Auth App** and supports both self‑service user operations and privileged admin workflows.

### Directory Structure:
```
users/
│
├── admin/
│   ├── services/
│   │   ├── user_service.py
│   │   └── profile_service.py
│   |
│   ├── repositories/
│   │   ├── users.py
│   │   └── profiles.py
│   |
│   ├── router.py
│   ├── schemas.py
│   └── dependencies.py
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

---

### The Users App handles:

### 1. User Management
- User creation (via Auth App)
- User retrieval
- User activation/deactivation (admin)
- Password reset (admin)
- Group assignment (RBAC)
- Listing and filtering users (admin)

---

### 2. User Profiles
- Profile creation
- Profile update
- Profile deletion
- Admin‑level profile creation for other users
- Avatar upload (S3-compatible storage)

---

### 3. RBAC (Role‑Based Access Control)
- Single‑group membership per user
- Three roles:
  - USER — basic access
  - MODERATOR — content management (movies, genres, actors, etc.)
  - ADMIN — full administrative privileges

Enforced via `require_role()` dependency:
```python
Depends(require_role(UserGroupEnum.ADMIN))
```
Examples:
- Movie creation/update/delete → MODERATOR or ADMIN
- User management → ADMIN only
- Profile self‑management → any authenticated user

---

### 4. Admin Console
- Manage users
- Change user groups
- Activate/deactivate accounts
- Reset passwords
- Create/update/delete profiles for any user
- Filter users by:
- Email
- Group
- Activation status
- Paginated user listing

#### Paginated User Listing
```
GET /api/v1/cinema/admin/users
```
Supports filtering by:
- `email` (substring match)
- `group` (`USER`, `MODERATOR`, `ADMIN`)
- `is_active` (`True`/`False`)

Returns a paginated list of users.

#### Change User Group
```
PATCH /api/v1/cinema/admin/users/{user_id}/group
```
Assigns a new group to a user.

#### Activate User
```
POST /api/v1/cinema/admin/users/{user_id}/activate
```
Sets `is_active = True`.

#### Deactivate User
```
POST /api/v1/cinema/admin/users/{user_id}/deactivate
```
Sets `is_active = False`.

#### Reset User Password (Admin)
```
POST /api/v1/cinema/admin/users/{user_id}/reset-password
```
Allows admins to set a new password for any user.

---

### 5. Admin‑Level Profile Management

Admins can create or update profiles for other users:
```
POST   /api/v1/cinema/admin/users/{user_id}/profile
PATCH  /api/v1/cinema/admin/users/{user_id}/profile
DELETE /api/v1/cinema/admin/users/{user_id}/profile
```
Supports:
- Creating profiles for users without one
- Updating any user’s profile
- Deleting any user’s profile

### 6. User Models
All user‑related models are located in:
```
users/models.py
```
This includes:

#### `User`
- Email
- Password hash
- Activation status
- Group (RBAC)
- Profile (1:1)
- Refresh tokens
- Likes, ratings, favorites
- Comments

#### `UserGroup`
- Defines available roles (`USER`, `MODERATOR`, `ADMIN`)
- One‑to‑many relationship with users

#### `UserProfile`
- First name
- Last name
- Gender
- Birth date
- Info
- Avatar URL (S3)

Enums are stored separately in:
```
users/enums.py
```

---

### 7. User Profiles
Users can manage their own profile via:
```
GET    /api/v1/cinema/users/me/profile
PATCH  /api/v1/cinema/users/me/profile
DELETE /api/v1/cinema/users/me/profile
```
Profile fields include:
- First name
- Last name
- Gender
- Birth date
- Info
- Avatar (uploaded to S3-compatible storage)

---

### 8. `/users/me` Endpoint
Authenticated users can retrieve their own profile and metadata:
```
GET /api/v1/cinema/users/me/
```
Response includes:
- Profile data
- Avatar URL
- User group
- Activation status
- Timestamps

---

### Architecture Summary
| Layer            | Responsibility                              |
| ---------------- | ------------------------------------------- |
| **Router**       | Defines API endpoints and RBAC requirements |
| **Service**      | Business logic, validation, orchestration   |
| **Repository**   | Database operations (SQLAlchemy)            |
| **Schemas**      | Request/response validation (Pydantic)      |
| **Dependencies** | DI wiring for services and repositories     |

This layered structure ensures clarity, testability, and maintainability.

---

### Summary
The Users App provides a complete, production‑ready user management system with:
- Full CRUD for user profiles
- Strong RBAC enforcement
- Moderator and admin privilege separation
- A robust admin console for managing users
- Password resets, activation, deactivation
- Filtering and pagination for large user bases
- Admin‑level profile creation, update, and deletion
- Clean layered architecture

It integrates seamlessly with the Auth App and the Movies App, forming a cohesive and scalable backend platform.



## ⭐ Movies App

The Movies App provides a complete domain model for movies, metadata, user interactions, and content relationships. It supports catalog browsing, filtering, sorting, reactions, ratings, favorites, and threaded comments. All relationships are explicitly modeled using SQLAlchemy with proper constraints, cascades, and association tables.

### Directory Structure:
```
movies/
│
├── router.py
├── genres_router.py
├── dependencies.py
├── service.py
├── repository.py
├── exceptions.py
├── utils.py
├── filters.py
├── schemas.py
└── models.py
```

---

### Movie App Models Overview
All movie‑related models are located in `movies/models.py`

This includes:
- `Movie`
- `Genre`
- `Star`
- `Director`
- `Certification`
- `MovieLike`
- `MovieRating`
- `FavoriteMovie`
- `MovieComment`

Association tables:
- `MoviesGenresModel`
- `MoviesStarsModel`
- `MoviesDirectorsModel`

---

### Data Model
Table: `movies`
| Column             | Type                            | Description                                      |
| ------------------ | ------------------------------- | ------------------------------------------------ |
| `id`               | `INTEGER` (PK)                  | Internal numeric identifier                      |
| `uu_id`            | `UUID`                          | Public unique identifier (generated by Postgres) |
| `name`             | `VARCHAR(255)`                  | Movie title                                      |
| `year`             | `INTEGER`                       | Release year                                     |
| `time`             | `INTEGER`                       | Duration in minutes                              |
| `imdb`             | `FLOAT`                         | IMDb rating                                      |
| `votes`            | `INTEGER`                       | Number of IMDb votes                             |
| `meta_score`       | `FLOAT` (nullable)              | Metascore rating                                 |
| `gross`            | `NUMERIC(15,2)` (nullable)      | Box office revenue                               |
| `description`      | `TEXT`                          | Movie synopsis                                   |
| `price`            | `NUMERIC(10,2)`                 | Purchase price                                   |
| `certification_id` | `INTEGER` (FK → certifications) | Age/content rating                               |

---

### Constraints
- Unique Constraint: (`name`, `year`, `time`)
  - Prevents duplicate movie entries.
- Foreign Key: `certification_id` → `certifications.id`  
  - Ensures valid content rating.

---

### Relationships
Movies are connected to several domain entities:

#### Genres
Many‑to‑many via `movies_genres` association table.
```python
genres: list[Genre]
```
#### Stars
Many‑to‑many via movies_stars.
```python
stars: list[Star]
```
#### Directors
Many‑to‑many via movies_directors.
```python
directors: list[Director]
```
#### Certification
One‑to‑many relationship.
```python
certification: Certification
```

---

### User Interaction Models
The Movies App includes several user‑interaction models that support likes, ratings, favorites, and comments. All of them enforce uniqueness constraints and cascade deletes when a movie or user is removed.

#### Movie Likes
Users can like or dislike a movie.
A user can have **only one reaction** per movie.
```python
class MovieLike:
    user_id: int
    movie_id: int
    is_like: bool
```
Constraints:
- Unique `(user_id, movie_id)`
- Cascade delete on user or movie removal

#### Movie Ratings
Users can rate a movie on a 1–10 scale.
A user can have **only one rating** per movie.
```python
class MovieRating:
    user_id: int
    movie_id: int
    rating: int
```
Constraints:
- Unique `(user_id, movie_id)`
- Cascade delete on user or movie removal

#### Favorite Movies
Users can add movies to their favorites list.
```python
class FavoriteMovie:
    user_id: int
    movie_id: int
```
Constraints:
- Unique `(user_id, movie_id)`
- Cascade delete on user or movie removal

#### Movie Comments (Threaded)
Users can leave comments on movies.
Comments support threaded replies via a **self‑referential** `parent_id`.
```python
class MovieComment:
    id: int
    movie_id: int
    user_id: int
    parent_id: int | None
    content: str
```
Features:
- Threaded replies (`parent` + `replies`)
- Cascade delete on movie or user removal
- Indexed for fast retrieval by movie, parent, and user

---

### Architecture
The Movie Domain follows the project’s layered architecture:

#### 1. Router Layer
Defines HTTP endpoints for:
- Listing movies
- Retrieving movie details
- Searching, filtering, sorting
- Admin CRUD operations (moderator‑only)

#### 2. Service Layer
Implements business logic:
- Validates movie existence
- Applies filtering and sorting rules
- Handles pagination
- Coordinates repository operations
- Logs domain events

#### 3. Repository Layer
Handles database operations:
- Fetch movies with or without relations
- Build dynamic SQL queries
- Execute search/filter/sort pipelines
- Manage CRUD operations

#### 4. Database Layer
Stores movies and all related entities with strict referential integrity.

---

### Catalog Features
The Movie Domain supports a flexible catalog system with:

#### Filtering
- By genre
- By year
- By certification
- By director
- By star
- By price range
- By IMDb rating

#### Sorting
- By newest
- By oldest
- By IMDb rating
- By Metascore
- By price
- By popularity (votes)

#### Searching
- Full‑text search by movie name
- Case‑insensitive matching

#### Pagination
- Efficient offset/limit pagination
- Consistent ordering via `default_order_by()`

---

### Design Goals
- Clean domain boundaries  
  - No cross‑imports between unrelated modules.
- Extensibility  
  - Designed to support future features such as likes, ratings, favorites, comments, purchases, and moderation.
- Performance  
  - Uses optimized SQL queries and eager loading where appropriate.
- Consistency  
  - All movie data is validated and normalized before persistence.

---

### Movie Model Summary
The `Movie` model aggregates all relationships:
```python
genres: list[Genre]
stars: list[Star]
directors: list[Director]
certification: Certification
likes: list[MovieLike]
ratings: list[MovieRating]
favorites: list[FavoriteMovie]
comments: list[MovieComment]
```
Additional fields:
- UUID (`uu_id`) generated by PostgreSQL
- Unique constraint on `(name, year, time)`
- Default ordering by `id DESC`

---

### Interaction Behavior
- Deleting a movie removes:
  - Likes
  - Ratings
  - Favorites
  - Comments
  - Association table entries

- Deleting a user removes:
  - Their likes
  - Their ratings
  - Their favorites
  - Their comments

- Moderators and admins can manage movies (CRUD)
- Users can:
  - Like/dislike
  - Rate
  - Favorite
  - Comment (with replies)
  - View reactions and rating summaries

---

### Summary
The Movies App provides a complete, production‑ready domain model with:
- Rich metadata (genres, stars, directors, certification)
- User interactions (likes, ratings, favorites, comments)
- Threaded comment system
- Strong relational integrity
- Proper cascading behavior
- Optimized indexing for performance
- Clean SQLAlchemy modeling

This forms the backbone of the Online Cinema platform’s catalog and user engagement features.


## ⭐ Movie Likes Feature
The Movie Likes subsystem enables authenticated users to express positive or negative reactions to movies. It is designed to be lightweight, scalable, and fully aligned with the project’s layered architecture (Router → Service → Repository → Database). The feature supports liking, disliking, removing reactions, and retrieving aggregated reaction statistics for each movie.

### Overview
Users can:
- Like a movie
- Dislike a movie
- Remove their reaction
- Fetch reaction summary for any movie (likes, dislikes, and the user’s own reaction)

Each user may have **only one reaction per movie**, enforced by a **composite primary key and a unique constraint**.

---

### Data Model
The `MovieLike` model represents a user’s reaction to a movie.

Table: `movie_likes`

| Column       | Type                    | Description                      |
| ------------ | ----------------------- | -------------------------------- |
| `user_id`    | `INTEGER` (FK → users)  | User who reacted                 |
| `movie_id`   | `INTEGER` (FK → movies) | Movie being reacted to           |
| `is_like`    | `BOOLEAN`               | `True` = like, `False` = dislike |
| `created_at` | `TIMESTAMP WITH TZ`     | Reaction timestamp               |

---

### Constraints
- Primary Key: (`user_id`, `movie_id`)
- Unique Constraint: (`user_id`, `movie_id`)
- Foreign Keys:
  - `user_id` → `users.id` (CASCADE on delete)
  - `movie_id` → `movies.id` (CASCADE on delete)

---

### Relationships
`User` → `MovieLike`:
A user can like/dislike many movies.
```python
user.movie_likes: list["MovieLike"]
```
`Movie` → `MovieLike`:
A movie can have many likes/dislikes.
```python
movie.likes: list["MovieLike"]
```

These relationships are defined using string‑based references to avoid circular imports and maintain clean domain boundaries.

---

### Architecture
The feature follows the project’s layered structure:

#### 1. Router Layer
Defines HTTP endpoints:
- `POST /movies/{id}/like`
- `POST /movies/{id}/dislike`
- `DELETE /movies/{id}/reaction`
- `GET /movies/{id}/reactions`

All endpoints require authentication and use `get_current_user` to obtain the active user.

#### 2. Service Layer
Implements business logic:
- Validates movie existence
- Upserts reactions
- Removes reactions
- Builds reaction summaries
- Logs domain events (e.g., “Like movie | user_id=1 movie_id=102”)

#### 3. Repository Layer
Handles database operations:
- Insert/update reaction
- Delete reaction
- Aggregate likes/dislikes using SQL conditional aggregation
- Fetch user’s reaction for a movie

#### 4. Database Layer
Stores reactions in the `movie_likes` table with strict referential integrity.

---

### Authentication
All reaction endpoints require a valid Bearer access token.
The authenticated user is resolved via:
```python
user: Annotated[User, Depends(get_current_user)]
```

---

### Design Goals
- Idempotent operations  
  - Repeated likes/dislikes do not create duplicates.
- Efficient aggregation  
  - Uses SQL `SUM(CASE WHEN ...)` for fast counts.
- Clean domain boundaries  
  - No cross‑module imports between `users` and `movies`.
- Scalable  
  - Supports millions of reactions with minimal overhead.


## ⭐ Movie Ratings (1–10 Scale)
The API includes a complete movie rating system that allows authenticated users to rate any movie on a 1–10 scale. Each user can rate a movie only once, and updating a rating simply overwrites the previous value. Ratings are stored efficiently using a composite primary key and exposed through clean, predictable endpoints.

### Feature Overview
Users can rate any movie with an integer value from 1 to 10
- Each user can have only one rating per movie
- Updating a rating overwrites the previous one
- Deleting a rating removes it entirely
- Rating summaries include:
  - average rating
  - total number of ratings
  - the current user’s rating

This feature integrates seamlessly with the existing movie domain and user authentication system.

---

### Database Design

Ratings are stored in the `movie_ratings` table:

| Column       | Type           | Notes                |
| ------------ | -------------- | -------------------- |
| `user_id`    | FK → `users.id`  | Part of composite PK |
| `movie_id`   | FK → `movies.id` | Part of composite PK |
| `rating`     | Integer (1–10) | Required             |
| `created_at` | Timestamp      | Auto‑generated       |

#### Why a composite primary key
The combination of `(user_id, movie_id)` **uniquely identifies a rating**.
This design:
- enforces the “**one rating per user per movie**” rule at the database level
- avoids unnecessary surrogate IDs
- **improves lookup performance**
- simplifies the domain model

Both foreign keys use `ondelete="CASCADE"`, ensuring that ratings are automatically removed if a user or movie is deleted.

---

### Rating Summary Logic
The API computes rating summaries using efficient SQL aggregation:
- `AVG(rating)` → average rating for the movie
- `COUNT(rating)` → total number of ratings
- user-specific query → the current user’s rating

If no ratings exist, the API returns:
```json
{
  "average_rating": null,
  "ratings_count": 0,
  "user_rating": null
}
```

---

### API Endpoints

#### 1. Rate a Movie
`POST /movies/{movie_id}/rating`
```json
{
  "rating": 8
}
```
Response:
```json
{
  "movie_id": 102,
  "average_rating": 8.0,
  "ratings_count": 1,
  "user_rating": 8
}
```

#### 2. Get Rating Summary
`GET /movies/{movie_id}/rating`

Returns the aggregated rating data for the movie.

#### 4. Delete Rating
`DELETE /movies/{movie_id}/rating`

Removes the user’s rating and returns the updated summary.

---

### Error Handling
The system uses domain‑level exceptions with FastAPI exception handlers.

Examples:
- `404 Not Found` — movie does not exist
- `422 Unprocessable` Entity — rating outside 1–10
- `401 Unauthorized` — missing or invalid token

This ensures consistent, predictable API responses.

---

### Integration with the Movie and User Domains
Ratings are exposed through the `Movie` model:
```python
# Movie model
ratings = relationship(
    "MovieRating",
    back_populates="movie",
    cascade="all, delete-orphan"
)

# User model
movie_ratings = relationship(
    "MovieRating",
    back_populates="user",
    cascade="all, delete-orphan"
)
```
This allows:
- automatic cleanup when movies are deleted
- easy access to rating data in higher‑level services
- clean domain modeling aligned with likes, genres, stars, and directors

## ⭐ Movie Favorites
The API includes a complete Favorites system that allows authenticated users to save movies to their personal favorites list and browse them using the full catalog functionality. Favorites behave like a personalized movie collection with support for search, filtering, sorting, and pagination.

### Feature Overview
- Add any movie to the user’s favorites
- Remove movies from favorites
- List all favorite movies with:
- search
- genre filtering
- year filtering
- IMDb filtering
- price filtering
- sorting (id, name, year, IMDb, votes, price)
- pagination
- Favorites list behaves exactly like the main movie catalog, but scoped to the user
- Favorites are stored efficiently using a composite primary key
- Cascade rules ensure favorites are removed automatically if a user or movie is deleted

This feature integrates seamlessly with the existing movie domain and user authentication system.

---

### Database Design
Favorites are stored in the `favorite_movies` table:

| Column       | Type           | Notes                |
| ------------ | -------------- | -------------------- |
| `user_id`    | FK → users.id  | Part of composite PK |
| `movie_id`   | FK → movies.id | Part of composite PK |
| `created_at` | Timestamp      | Auto‑generated       |

#### Why a composite primary key
The combination of `(user_id, movie_id)` uniquely identifies a favorite entry.
This design:
- enforces “**one favorite per user per movie**” at the database level
- avoids unnecessary surrogate IDs
- **improves lookup performance**
- simplifies the domain model

Both foreign keys use `ondelete="CASCADE"`, ensuring favorites are automatically removed if a user or movie is deleted.

---

### API Endpoints

#### 1. Add to Favorites
`POST /movies/{movie_id}/favorite`
```json
{
  "movie_id": 102,
  "is_favorite": true
}
```

#### 2. Remove from Favorites
`DELETE /movies/{movie_id}/favorite`
```json
{
  "movie_id": 102,
  "is_favorite": false
}
```

#### 3. List Favorite Movies
`GET /movies/favorites`

Supports all catalog parameters:
```
/movies/favorites?genre_id=3&search=action&sort_by=imdb&order=desc&page=1&size=20
```
Response (FastAPI Pagination):
```json
{
  "items": [
    {
      "id": 102,
      "name": "Inception",
      "year": 2010,
      "imdb": 8.8,
      "description": "...",
      "is_favorite": true
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

---

### How Favorites Integrate with Filtering & Sorting
The favorites list uses the same filtering and sorting logic as the main movie catalog.
This is achieved by:

- Building a base query that selects only the user’s favorite movies:
```python
select(Movie)
    .join(FavoriteMovie)
    .where(FavoriteMovie.user_id == user_id)
```
- Passing this base query into the shared `build_movie_filter_query()` function.
- Applying search, genre filters, year filters, IMDb filters, price filters, and sorting on top of the favorites query.

This keeps the architecture clean, modular, and consistent.

---

### Integration with the Movie and User Domains
Favorites are exposed through the `Movie` and `User` models:
```python
# Movie model
favorites: Mapped[list["FavoriteMovie"]] = relationship(
        "FavoriteMovie",
        back_populates="movie",
        cascade="all, delete-orphan"
    )

# User model
favorite_movies: Mapped[list["FavoriteMovie"]] = relationship(
        "FavoriteMovie",
        back_populates="user",
        cascade="all, delete-orphan"
    )
```
This allows:
- automatic cleanup when movies or users are deleted
- easy access to favorites in higher‑level services
- consistent domain modeling alongside likes and ratings

## ⭐ Favorite Status in Movie List & Detail Responses
The API automatically annotates each movie with an `is_favorite` flag, allowing clients to easily determine whether the authenticated user has added a movie to their favorites. This behavior applies to both:
- Movie list responses (`GET /movies`)
- Movie detail responses (`GET /movies/{movie_id}`)

This makes it easy for frontends to display “favorite” icons, highlight saved movies, or toggle favorites without additional API calls.

### Feature Overview
When a user is authenticated, the API:
- Retrieves the user’s favorite movie IDs
- Annotates each movie in the list with `is_favorite`: true or false
- Annotates the movie detail response with the same flag

This ensures consistent behavior across all endpoints.

---

### Movie List Response Example
`GET /movies?sort_by=imdb&order=desc&page=1&size=20`
```json
{
  "items": [
    {
      "id": 102,
      "name": "Inception",
      "year": 2010,
      "imdb": 8.8,
      "description": "A thief who steals corporate secrets...",
      "is_favorite": true
    },
    {
      "id": 205,
      "name": "Interstellar",
      "year": 2014,
      "imdb": 8.6,
      "description": "A team of explorers travel...",
      "is_favorite": false
    }
  ],
  "total": 2,
  "page": 1,
  "size": 20
}
```

#### Key points:
- `is_favorite` is included for every movie
- Pagination and filtering
- No additional API calls are required to determine favorite status

---

### Movie Detail Response Example
`GET /movies/102`
```json
{
  "id": 102,
  "uu_id": "c0a801f4-5e2a-4b1e-9f7a-1b2c3d4e5f6a",
  "name": "Inception",
  "year": 2010,
  "time": 148,
  "imdb": 8.8,
  "votes": 2000000,
  "description": "A thief who steals corporate secrets...",
  "meta_score": 74,
  "gross": "292.58",
  "price": "4.99",
  "certification": { ... },
  "genres": [ ... ],
  "stars": [ ... ],
  "directors": [ ... ],
  "is_favorite": true
}
```

#### Key points:
- The detail response now includes `is_favorite`
- This allows frontends to show a filled/empty “favorite” icon
- No need to call `/movies/{id}/favorite` just to check status

---

### Implementation Notes
- The `is_favorite` flag is computed efficiently using a **bulk lookup of the user’s favorite movie IDs**.
- No N+1 queries are performed.
- The flag is added dynamically at the service layer and does not affect the database schema.
- The behavior is consistent across:
  - movie list
  - movie detail
  - favorites list

## ⭐ Movie Comments: Threaded Replies + Real‑Time Notifications
The Online Cinema platform includes a fully‑featured movie comments system with:
- Threaded (nested) replies
- Email notifications for comment replies (via Celery + Mailhog)
- Real‑time WebSocket notifications for online users
- JWT‑authenticated WebSocket connections
- Cascade deletion and clean relational structure
- Production‑grade error handling and connection management

This subsystem is designed for scalability, clarity, and maintainability.

### Architecture Overview
Components involved:
| Component              | Responsibility                                          |
| ---------------------- | ------------------------------------------------------- |
| **`MovieComment` model** | Stores comments, replies, timestamps, and relationships |
| **`MovieService`**       | Business logic for creating and listing comments        |
| **Celery Worker**      | Sends email notifications asynchronously                |
| **Mailhog**            | Local SMTP server for testing email delivery            |
| **WebSocket Router**   | Handles authenticated WS connections                    |
| **`ConnectionManager`**  | Tracks active user WebSocket sessions                   |
| **JWT WebSocket Auth** | Validates tokens passed via query params                |

---

### `MovieComment` Model & Database Design
The MovieComment model is the backbone of the commenting system. It supports **threaded replies, cascade deletion, fast lookups**, and **clean relational integrity**.

This section documents the model’s structure, relationships, and indexing strategy.

Each comment is represented by a MovieComment record with the following fields:
| Field        | Type       | Description      |                                           |
| ------------ | ---------- | ---------------- | ----------------------------------------- |
| `id`         | `int`      | Primary key      |                                           |
| `movie_id`   | `int`      | FK → `movies.id` |                                           |
| `user_id`    | `int`      | FK → `users.id`  |                                           |
| `parent_id`  | `int`      | `null`           | Self‑referential FK → `movie_comments.id` |
| `content`    | `text`     | Comment text     |                                           |
| `created_at` | `datetime` | Timestamp (UTC)  |                                           |
| `updated_at` | `datetime` | Timestamp (UTC)  |                                          `

---

### Relationships
#### 1. Movie → Comments

A movie can have many comments:
```python
movie = relationship("Movie", back_populates="comments")
```
#### 2. User → Comments
A user can author many comments:
```python
user = relationship("User", back_populates="movie_comments")
```
#### 3. Self‑referential Parent → Replies
This is what enables threaded replies:
```python
parent = relationship(
    "MovieComment",
    remote_side=[id],
    backref="replies"
)
```
This means:
- A comment may have zero or one parent
- A comment may have zero or many replies
- Replies can be nested indefinitely (though UI typically limits depth)

---

### Cascade Behavior
All foreign keys use `ON DELETE CASCADE`:
- Deleting a **movie** removes all its comments
- Deleting a **user** removes all their comments
- Deleting a **parent** comment removes all nested replies

This ensures the database stays clean without orphaned records.

---

### Indexing Strategy
To support fast queries, especially on large datasets, the following indexes are created:
| Index                         | Column      | Purpose                                                |
| ----------------------------- | ----------- | ------------------------------------------------------ |
| `ix_movie_comments_movie_id`  | `movie_id`  | Fast lookup of comments for a movie                    |
| `ix_movie_comments_parent_id` | `parent_id` | Fast lookup of replies                                 |
| `ix_movie_comments_user_id`   | `user_id`   | Fast lookup of comments by user (moderation, profiles) |
These indexes dramatically improve performance for:
- Listing comments for a movie
- Fetching replies for a comment
- Moderation tools (e.g., “show all comments by user”)

---

### Commenting Flow

#### 1. User posts a top‑level comment
`POST /api/v1/cinema/movies/{movie_id}/comments`
- Comment is stored in DB
- No notifications are sent
- Response includes comment metadata

#### 2. User posts a reply
`POST /api/v1/cinema/movies/{movie_id}/comments`

Payload example:
```json
{
  "content": "This is a reply!",
  "parent_id": 42
}
```
When a reply is created:
- The parent comment’s author receives an email notification
- If the parent author is connected via WebSocket, they receive a real‑time push notification

---

### Email Notifications (Celery + Mailhog)
Reply notifications are sent asynchronously using Celery:
- Task: `send_comment_reply_notification`
- Template: `comment_reply.html`
- SMTP: Mailhog (`localhost:1025`)
- View emails at: `http://localhost:8025`

This ensures the API remains fast and responsive.

---

### Real‑Time Notifications (WebSocket)
Users can subscribe to comment notifications via:
```
ws://localhost:8000/api/v1/cinema/ws/comments?token=<JWT>
```

#### **Features**:
- **JWT authentication** (token passed via query param)
- **Multiple simultaneous connections per user**
- **Automatic cleanup on disconnect**
- **JSON‑formatted notification payloads**

#### Example WebSocket message:
```json
{
  "type": "comment_reply",
  "movie_id": 1,
  "comment_id": 57,
  "parent_id": 42,
  "content": "Replying to your comment!",
  "created_at": "2026-02-24T10:15:00Z"
}
```

---

### WebSocket Authentication
WebSockets do not support FastAPI’s dependency injection for OAuth2, so authentication is handled manually:
- Client passes `?token=<JWT>` in the URL
- Server decodes and validates the token
- User is loaded from the database
- Invalid tokens result in a clean WebSocket close (`1008`)

This approach is robust and production‑safe.

---

### Testing the Feature

#### 1. Connect WebSocket (Browser Console)
```js
const token = "<JWT>";
const ws = new WebSocket(`ws://localhost:8000/api/v1/cinema/ws/comments?token=${token}`);

ws.onopen = () => console.log("Connected");
ws.onmessage = (e) => console.log("WS Notification:", JSON.parse(e.data));
ws.onclose = () => console.log("Closed");
```

#### 2. Add a top‑level comment (Postman)
```
POST /api/v1/cinema/movies/1/comments
Authorization: Bearer <JWT>

{
  "content": "Great movie!"
}
```

#### 3. Add a reply (Postman)
```
POST /api/v1/cinema/movies/1/comments
Authorization: Bearer <JWT>

{
  "content": "I agree!",
  "parent_id": 1
}
```
Expected results:
- Email appears in Mailhog
- WebSocket receives a JSON notification

---

### Connection Manager
The WebSocket manager tracks active connections:
- `user_id → [WebSocket, WebSocket, ...]`
- Supports multiple browser tabs
- Sends notifications to all active sessions
- Cleans up on disconnect

This makes the system horizontally scalable.

---

### Summary
This feature delivers a complete, modern commenting experience:
- Threaded replies
- Email notifications
- Real‑time WebSocket updates
- Clean architecture
- Production‑ready error handling
- Fully testable with Postman + Mailhog + browser console

## ⭐ Database Migrations (Local + Docker)
This project uses Alembic for SQLAlchemy schema migrations.
Migrations are generated locally and applied inside Docker using a dedicated migrator service.

This section explains:
- How migrations work
- How to generate them locally
- How Docker applies them
- Why two Alembic config files exist
- How the project structure is wired

---

### Project Structure (relevant to Alembic)
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

---

### Why Two Alembic Config Files
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

---

### Local Migration Workflow
1. Ensure local PostgreSQL is running
2. Generate a migration:

```shell
poetry run alembic -c alembic.local.ini revision --autogenerate -m "message"
```
3. Review the generated file in `alembic/versions/`
4. Commit it to Git

---

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

## ⭐ MailHog Integration (Local Email Testing)
The project includes full integration with MailHog, a lightweight SMTP testing server used during development. MailHog captures outgoing emails (activation, password reset, notifications) without sending them to real inboxes. This allows safe, repeatable testing of all email‑related features.

### How MailHog Works
MailHog provides two separate interfaces:

#### 1. SMTP Server (Port 1025)
Used by the FastAPI backend to send emails.
- Accepts plain SMTP only
- Does not support STARTTLS
- Does not support SMTP AUTH
- Always accepts connections without authentication

#### 2. Web UI (Port 8025)
Used by developers to view captured emails.
- Can be protected with HTTP Basic Auth
- Authentication is configured via `MAILHOG_USER` and `MAILHOG_PASSWORD`

These two interfaces are completely independent.

---

### MailHog Authentication Explained
MailHog supports only HTTP UI authentication, not SMTP authentication.

#### HTTP UI Authentication
Configured via:
```
MAILHOG_USER=admin
MAILHOG_PASSWORD=some_password
```
A startup script generates `/mailhog.auth`:
```
echo "$MAILHOG_USER:$HASHED_PASSWORD" > /mailhog.auth
```
Docker passes this file to MailHog:
```yml
environment:
  MH_AUTH_FILE: /mailhog.auth
```
This protects the Web UI at:
```
http://localhost:8025
```

#### ❌ SMTP Authentication
MailHog does not support:
- AUTH LOGIN
- AUTH PLAIN
- SMTP username/password
- TLS or STARTTLS

Any attempt to use TLS or SMTP auth will fail.

---

### FastAPI Email Configuration

The backend loads SMTP settings from `.env`:
```
SMTP_SERVER=cinema-mailhog
SMTP_PORT=1025
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=false
```
These values are injected into the `EmailSender` class:
```python
smtp = aiosmtplib.SMTP(
    hostname=self._hostname,
    port=self._port,
    start_tls=self._use_tls
)
```
#### For MailHog:
- `SMTP_USE_TLS` must be false
- `SMTP_USERNAME` and `SMTP_PASSWORD` must be empty strings
- TLS and authentication are automatically skipped

This allows the `EmailSender` to work with both:
- MailHog (local development)
- Real SMTP providers (production)

without any code changes.

---

### Running MailHog
MailHog is included in `docker-compose.yml`:
```yml
mailhog:
  build:
    context: .
    dockerfile: ./docker/mailhog/Dockerfile
  command: ["/bin/bash", "-c", "/commands/setup_mailhog_auth.sh && /go/bin/MailHog"]
  ports:
    - "8025:8025"
    - "1025:1025"
  env_file:
    - .env
  environment:
    MH_AUTH_FILE: /mailhog.auth
```
#### Access the Web UI
```
http://localhost:8025
```
#### Log in using:
```
MAILHOG_USER / MAILHOG_PASSWORD
```

---

### Testing Email Delivery
- Register a new user or trigger a password reset
- Open MailHog UI
- View captured emails under the “Inbox” tab
- Inspect HTML templates, links, and formatting

No real emails are sent.

## ⭐ Redis Caching Architecture for the Movie Catalog
Caching is a core performance feature of the Movie Catalog service. The system uses Redis as a high‑speed, in‑memory cache to reduce database load, accelerate API responses, and provide a smoother user experience. The caching layer is designed around three principles: speed, correctness, and isolation per user.

### What is Cached
The service caches data that is expensive to compute or frequently requested:
- Movie lists — paginated, sorted, and filtered results
- Movie details — full metadata, genres, directors, stars
- User reactions — likes/dislikes summary per movie
- Rating summaries — aggregated rating data
- Genre lists — with movie counts

Each cache entry is scoped by user where appropriate to ensure personalization does not leak across accounts.

### Cache Key Structure
Keys follow a predictable, namespaced pattern:
- `movies:list:{user_id}:{hash}` — cached movie list for a specific user and filter set
- `movie:{movie_id}:detail:{user_id}` — movie detail with user‑specific fields
- `movie:{movie_id}:reactions:user:{user_id}` — reaction summary
- `movie:{movie_id}:rating_summary:user:{user_id}` — rating summary
- `genres:with_count` — cached genre list

This structure makes invalidation targeted and efficient.

### How Invalidation Works
Caching is only useful if stale data is never returned.

The service uses event‑driven invalidation: whenever a user performs an action that changes data, only the affected cache keys are removed.

Key invalidation rules include:
- Movie created/updated/deleted
  - Invalidate all movie lists: `movies:list:*`
  - Invalidate movie detail for all users:`movie:{movie_id}:detail:*`
- User likes/dislikes a movie
  - Invalidate reaction summary for that user: `movie:{movie_id}:reactions:user:{user_id}`
  - Invalidate that user’s movie lists:`movies:list:{user_id}:*`
- User rates a movie
  - Invalidate rating summary for that user: `movie:{movie_id}:rating_summary:user:{user_id}`
- Genres updated
  - Invalidate: `genres:with_count`

This approach ensures correctness **without wiping the entire cache** unnecessarily.

### TTL and Expiration Strategy
Each cached entry has a configurable TTL (default: 10 minutes). This provides:
- Automatic cleanup of unused keys
- Protection against long‑term stale data
- A balance between performance and freshness

TTL is intentionally short for user‑specific data (reactions, ratings) and longer for static data (genres).

### Performance Impact
Redis caching significantly reduces response latency and database load.

Endpoints that previously required multiple joins, aggregations, or user‑specific computations now return almost instantly when served from cache.

This improves throughput under load and provides a smoother user experience.

Caching is especially beneficial for endpoints that combine multiple joins, aggregations, or user‑specific computations.

### Reliability and Safety
The caching layer is designed to fail gracefully:
- If Redis is unavailable, the service falls back to database queries.
- Cache writes are non‑blocking and never affect the main request flow.
- All cached values are JSON‑encoded using Pydantic’s safe encoder to avoid serialization issues (e.g., `Decimal`, `datetime`, `UUID`).

## ⭐ Database Seeding System
The project includes a complete, asynchronous database seeding system designed to populate the initial dataset for the Online Cinema platform. It generates JSON seed files (if missing) and loads them into the database in a safe, idempotent way.

The seeding system is fully automated and can be run at any time without duplicating data.

### What the Seeder Does
The seeding system performs the following tasks:

#### 1. Generate JSON seed files (if missing)
The generator creates structured JSON files for:
- Certifications
- Genres
- Movies
- Stars
- Directors

These files are stored under:
```
src/seeding/seed_data/
```
If any file is missing, it will be generated automatically.

#### 2. Fetch random names for stars and directors
The generator uses:
```
https://randomuser.me/api/
```
to fetch realistic names.
If the API is unavailable, it falls back to a predefined list of names.

#### 3. Insert base data into the database
The seeder loads JSON files and inserts:
- Certifications
- Genres
- Stars
- Directors
- Movies

All inserts are idempotent — existing rows are detected and skipped.

#### 4. Create movie associations
Randomized associations are created:
- Movie → Genres (up to 3)
- Movie → Stars (up to 5)
- Movie → Director (1)

#### 5. Seed user groups (RBAC)
The seeder ensures the following groups exist:
- USER
- MODERATOR
- ADMIN

These are required for RBAC and admin console functionality.

#### 6. Commit all changes
All inserts and associations are committed in a single transaction.

---

### Configuration

Paths to JSON files are defined in:
```
config.py
```
Example:
```python
CERT_JSON_PATH = "src/seeding/seed_data/certifications.json"
MOVIE_JSON_PATH = "src/seeding/seed_data/movies.json"
GENRE_JSON_PATH = "src/seeding/seed_data/genres.json"
STARS_JSON_PATH = "src/seeding/seed_data/stars.json"
DIRECTORS_JSON_PATH = "src/seeding/seed_data/directors.json"
```
These can be overridden via `.env` if needed.

---

### JSON Generation
The generator (`JsonDataGenerator`) creates:

#### Certifications
- Static list: `G`, `PG`, `PG‑13`, `R`, `NC‑17`.

#### Genres
- Static list of 20+ genres.

#### Movies
Randomized fields:
- Name
- Year
- Runtime
- IMDb rating
- Votes
- Meta score
- Gross revenue
- Description
- Price
- Certification

#### Stars & Directors
Fetched from `randomuser.me` with fallback names.

---

### Database Population
The seeder (`InitialDatabaseSeeder`) performs:

#### 1. Insert unique rows
Using `_insert_unique_by_name()`:
- Avoids duplicates
- Returns a mapping of `{name → id}`

#### 2. Insert movies
- Movies reference certifications via `certification_id`.

#### 3. Insert associations
Randomized many‑to‑many relationships:
- `MoviesGenresModel`
- `MoviesStarsModel`
- `MoviesDirectorsModel`

#### 4. Seed user groups
Ensures RBAC groups exist:
```python
USER, MODERATOR, ADMIN
```

---

### Running the Seeder
Run the seeding script:
```
python src/seeding/populate_db.py
```
This will:
- Generate missing JSON files
- Populate the database
- Create associations
- Seed user groups

The process is **fully asynchronous** and **logs progress to the console**.

---

### Architecture Summary
| Component               | Responsibility                                                               |
| ----------------------- | ---------------------------------------------------------------------------- |
| `JsonDataGenerator`     | Generates JSON seed files (certifications, genres, movies, stars, directors) |
| `InitialDatabaseSeeder` | Loads JSON files and inserts data into the database                          |
| `config.py`             | Defines paths to seed files and environment configuration                    |
| `seed_data/`            | Stores generated JSON files                                                  |
| `populate_db.py`        | Orchestrates the entire seeding process                                      |

---

### Summary
The seeding system provides:
- Automatic JSON generation
- Idempotent database population
- Randomized movie metadata
- Realistic star/director names
- Complete RBAC group initialization
- Fully asynchronous implementation
- Clean separation of concerns

This ensures that the Online Cinema platform always starts with a rich, consistent dataset suitable for development, testing, and demos.

## ⭐ Running the Project with Docker Compose
The project includes a full Docker Compose setup that launches all required services for local development or demo environments. This setup ensures a consistent environment across machines and eliminates the need to install Postgres, MinIO, or Mailhog manually.

### Services Included in docker-compose.yml
The Compose stack typically includes:

#### 1. FastAPI application  
Runs the backend server with all API routes, WebSocket notifications, RBAC, admin console, and business logic.

#### 2. PostgreSQL database  
Stores all application data: users, profiles, movies, ratings, likes, favorites, comments, and RBAC groups.

#### 3. MinIO (S3-compatible storage)  
Used for storing user avatars and other media assets.

#### 4. Mailhog  
Captures outgoing emails (activation, password reset) for local testing.

#### 5. Celery worker + Celery beat  
Handles background tasks such as sending emails.

#### 6. Redis  
Used as the Celery broker and result backend.

#### 7. Database seeding container  
Automatically generates JSON seed files and populates the database with:
- User groups (`USER`, `MODERATOR`, `ADMIN`)
- Certifications
- Genres
- Stars
- Directors
- Movies
- Movie associations (genres, stars, directors)

---

### Environment Configuration
All environment variables are loaded from `.env` using Pydantic Settings.

Use `.env.sample` file to define `.env` variables.

The seeding system also uses paths defined in config.py:
```python
CERT_JSON_PATH=src/seeding/seed_data/certifications.json
MOVIE_JSON_PATH=src/seeding/seed_data/movies.json
GENRE_JSON_PATH=src/seeding/seed_data/genres.json
STARS_JSON_PATH=src/seeding/seed_data/stars.json
DIRECTORS_JSON_PATH=src/seeding/seed_data/directors.json
```
These are generated automatically if missing.

---

### Starting the Entire Stack
From the project root:
```
docker compose up --build
```
This will:
- Build the FastAPI application image
- Start Postgres, Redis, MinIO, Mailhog
- Start Celery worker and beat
- Run the database seeding container
- Launch the FastAPI server

Once everything is up, the API is available at:
```
http://localhost:8000
```

Interactive docs:
```
http://localhost:8000/docs
```

---

### Database Seeding on Startup
The seeding container runs:
```
python src/seeding/populate_db.py
```
This script:
- Generates JSON seed files if missing
- Seeds user groups (`USER`, `MODERATOR`, `ADMIN`)
- Loads certifications, genres, stars, directors, movies
- Inserts associations (movie → genres, stars, directors)
- Commits everything in a single transaction

The seeding process is **idempotent** — running it multiple times will not duplicate data.

---

### Useful Docker Commands
#### 1. Rebuild everything
```
docker compose up --build
```

#### 2. Run in detached mode
```
docker compose up -d
```

#### 3. Stop all services
```
docker compose down
```

#### 4. Remove volumes (reset database)
```
docker compose down -v
```

#### 5. View logs
```
docker compose logs -f
```

---

### Development Workflow
- Modify backend code → Docker automatically reloads if using bind mounts
- Database changes → run migrations or reset with `down -v`
- Seed data → automatically applied on first startup

This setup ensures a smooth development experience without manual environment setup.