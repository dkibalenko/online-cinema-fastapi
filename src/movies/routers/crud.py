from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi_pagination import Page

from auth.dependencies import get_current_user, require_role
from movies.dependencies import get_movie_reaction_service, get_movie_service
from movies.schemas import (
    FavoriteMovieListSchema,
    MovieCreateSchema,
    MovieDetailSchema,
    MovieFilterParams,
    MovieListItemSchema,
    MovieSortParams,
    MovieUpdateSchema,
)
from movies.services import MovieReactionService, MovieService
from rate_limiting import limiter
from users.enums import UserGroupEnum
from users.models import User

router = APIRouter(prefix="/movies", tags=["Movies"])


# --- static routes first ---


@router.get(
    "",
    response_model=Page[MovieListItemSchema],
    summary="List Movies",
    description=(
        "Retrieve a paginated list of movies with optional "
        "filtering and sorting. "
        "Movies are annotated with 'is_favorite' field indicating "
        "if the current user has favorited them. "
        "Filtering options include genre ID, release year, min IMDb rating, "
        "min/max price. "
        "Sorting options include ID, name, year, IMDb, votes, price."
        "Search by title, description, star, or director is also supported."
        "Order can be ascending or descending."
    ),
    responses={200: {"description": "List of movies retrieved successfully"}},
    status_code=status.HTTP_200_OK,
)
@limiter.limit("60/minute")
async def list_movies(
    request: Request,
    filter_query: Annotated[MovieFilterParams, Depends()],
    sort_query: Annotated[MovieSortParams, Depends()],
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> Page[MovieListItemSchema]:
    """Retrieve a paginated list of movies with optional filtering and sorting.

    Movies are annotated with 'is_favorite' field indicating if the current
    user has favorited them.
    """
    return await service.get_movie_list(user.id, filter_query, sort_query)


@router.post(
    "",
    dependencies=[
        Depends(require_role(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    response_model=MovieDetailSchema,
    summary="Create Movie",
    description=(
        "Create a new movie. Requires MODERATOR or ADMIN role. "
        "The creator will be set as the movie's author."
    ),
    responses={
        201: {"description": "Movie created successfully"},
        400: {"description": "Bad Request - invalid input data"},
        401: {"description": "Unauthorized - invalid or missing token"},
        403: {"description": "Forbidden - insufficient permissions"},
        409: {"description": "Conflict - movie with same data already exists"},
    },
    status_code=status.HTTP_201_CREATED,
)
async def create_movie(
    data: MovieCreateSchema,
    service: Annotated[MovieService, Depends(get_movie_service)],
) -> MovieDetailSchema:
    """Create a new movie. Requires MODERATOR or ADMIN role."""
    return await service.create_movie(data)


@router.get(
    "/favorites",
    response_model=Page[FavoriteMovieListSchema],
    summary="List user's favorite movies",
    description=(
        "Retrieve a paginated list of the user's favorite movies. "
        "Supports the same filtering & sorting options as the main movie list."
    ),
    responses={
        200: {"description": "List of favorite movies retrieved successfully"},
        401: {"description": "Unauthorized - invalid or missing token"},
    },
    status_code=status.HTTP_200_OK,
)
async def list_favorites(
    filter_query: Annotated[MovieFilterParams, Depends()],
    sort_query: Annotated[MovieSortParams, Depends()],
    service: Annotated[
        MovieReactionService, Depends(get_movie_reaction_service)
    ],
    user: Annotated[User, Depends(get_current_user)],
) -> Page[FavoriteMovieListSchema]:
    """Retrieve a paginated list of the user's favorite movies."""
    return await service.list_favorites(user.id, filter_query, sort_query)


# --- dynamic routes below ---


@router.get(
    "/{movie_id}",
    response_model=MovieDetailSchema,
    summary="Get Movie",
    description=(
        "Retrieve detailed information about a specific movie by its ID. "
        "The response includes all movie details along with an 'is_favorite' "
        "field indicating if the current user has favorited the movie."
    ),
    responses={
        200: {"description": "Movie details retrieved successfully"},
        401: {"description": "Unauthorized - invalid or missing token"},
        404: {"description": "Not Found - movie does not exist"},
    },
    status_code=status.HTTP_200_OK,
)
@limiter.limit("60/minute")
async def get_movie(
    request: Request,
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> MovieDetailSchema:
    """Retrieve detailed information about a specific movie by its ID."""
    return await service.get_movie_detail(movie_id, user.id)


@router.patch(
    "/{movie_id}",
    dependencies=[
        Depends(require_role(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    response_model=MovieDetailSchema,
    summary="Update Movie",
    description=(
        "Update an existing movie. Requires MODERATOR or ADMIN role. "
        "Only provided fields will be updated."
    ),
    responses={
        200: {"description": "Movie updated successfully"},
        400: {"description": "Bad Request - invalid input data"},
        401: {"description": "Unauthorized - invalid or missing token"},
        403: {"description": "Forbidden - insufficient permissions"},
        404: {"description": "Not Found - movie does not exist"},
    },
    status_code=status.HTTP_200_OK,
)
async def update_movie(
    movie_id: int,
    data: MovieUpdateSchema,
    service: Annotated[MovieService, Depends(get_movie_service)],
) -> MovieDetailSchema:
    """Update an existing movie. Requires MODERATOR or ADMIN role."""
    return await service.update_movie(movie_id, data)


@router.delete(
    "/{movie_id}",
    dependencies=[
        Depends(require_role(UserGroupEnum.MODERATOR, UserGroupEnum.ADMIN))
    ],
    summary="Delete Movie",
    description=(
        "Delete an existing movie. Requires MODERATOR or ADMIN role."
    ),
    responses={
        204: {"description": "Movie deleted successfully"},
        401: {"description": "Unauthorized - invalid or missing token"},
        403: {"description": "Forbidden - insufficient permissions"},
        404: {"description": "Not Found - movie does not exist"},
    },
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_movie(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
):
    """Delete an existing movie. Requires MODERATOR or ADMIN role."""
    await service.delete_movie(movie_id)
