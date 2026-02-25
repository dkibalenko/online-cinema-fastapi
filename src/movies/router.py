from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi_pagination import Page

from rate_limiting import limiter
from movies.dependencies import get_movie_service
from movies.schemas import (
    MovieCreateSchema,
    MovieDetailSchema,
    MovieListItemSchema,
    MovieUpdateSchema,
    MovieFilterParams,
    MovieSortParams,
    MovieReactionActionResponseSchema,
    MovieReactionSummarySchema,
    MovieRatingCreateSchema,
    MovieRatingSummarySchema,
    FavoriteMovieResponseSchema,
    FavoriteMovieListSchema,
    CommentCreateSchema,
    CommentSchema,
)
from movies.service import MovieService
from auth.dependencies import get_current_user, require_role
from users.models import User
from users.enums import UserGroupEnum


router = APIRouter(prefix="/movies", tags=["movies"])


# static endpoints must be placed above any {movie_id} routes
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
    responses={
        200: {"description": "List of movies retrieved successfully"}
    },
    status_code=status.HTTP_200_OK
)
@limiter.limit("60/minute")
async def list_movies(
    filter_query: Annotated[MovieFilterParams, Depends()],
    sort_query: Annotated[MovieSortParams, Depends()],
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)]
) -> Page[MovieListItemSchema]:
    return await service.get_movie_list(
        user.id,
        filter_query,
        sort_query
    )


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
    status_code=status.HTTP_201_CREATED)
async def create_movie(
    data: MovieCreateSchema,
    service: Annotated[MovieService, Depends(get_movie_service)]
) -> MovieDetailSchema:
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
    status_code=status.HTTP_200_OK
)
async def list_favorites(
    filter_query: Annotated[MovieFilterParams, Depends()],
    sort_query: Annotated[MovieSortParams, Depends()],
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)]
) -> Page[FavoriteMovieListSchema]:
    return await service.list_favorites(
        user.id,
        filter_query,
        sort_query,
    )


# dynamic endpoints
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
    status_code=status.HTTP_200_OK
)
@limiter.limit("60/minute")
async def get_movie(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)]
) -> MovieDetailSchema:
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
    status_code=status.HTTP_200_OK
)
async def update_movie(
    movie_id: int,
    data: MovieUpdateSchema,
    service: Annotated[MovieService, Depends(get_movie_service)]
) -> MovieDetailSchema:
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
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_movie(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)]
):
    await service.delete_movie(movie_id)

@router.post(
    "/{movie_id}/like",
    response_model=MovieReactionActionResponseSchema,
    summary="Like a movie",
    description=(
        "Like a movie. If the user has already liked the movie, "
        "this action will have no effect."
    ),
    responses={
        200: {"description": "Movie liked successfully"},
        401: {"description": "Unauthorized - invalid or missing token"},
        404: {"description": "Not Found - movie does not exist"},
    },
    status_code=status.HTTP_200_OK,
)
@limiter.limit("20/minute")
async def like_movie(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> MovieReactionActionResponseSchema:
    return await service.like_movie(user_id=user.id, movie_id=movie_id)


@router.post(
    "/{movie_id}/dislike",
    response_model=MovieReactionActionResponseSchema,
    summary="Dislike a movie",
    description=(
        "Dislike a movie. If the user has already disliked the movie, "
        "this action will have no effect."
    ),
    responses={
        200: {"description": "Movie disliked successfully"},
        401: {"description": "Unauthorized - invalid or missing token"},
        404: {"description": "Not Found - movie does not exist"},
    },
    status_code=status.HTTP_200_OK,
)
@limiter.limit("20/minute")
async def dislike_movie(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> MovieReactionActionResponseSchema:
    return await service.dislike_movie(user_id=user.id, movie_id=movie_id)


@router.delete(
    "/{movie_id}/reaction-remove",
    response_model=MovieReactionActionResponseSchema,
    summary="Remove like/dislike from a movie",
    description=(
        "Remove user's like or dislike from a movie. If the user has not "
        "reacted to the movie, this action will have no effect."
    ),
    responses={
        200: {"description": "Movie reaction removed successfully"},
        401: {"description": "Unauthorized - invalid or missing token"},
        404: {"description": "Not Found - movie does not exist"},
    },
    status_code=status.HTTP_200_OK,
)
async def remove_movie_reaction(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)],
) -> MovieReactionActionResponseSchema:
    return await service.remove_movie_reaction(
        user_id=user.id, movie_id=movie_id
    )


@router.get(
    "/{movie_id}/reactions",
    response_model=MovieReactionSummarySchema,
    summary="Get movie reactions summary",
    description=(
        "Retrieve a summary of reactions for a specific movie, including "
        "total likes, total dislikes, and the current user's reaction status "
        "(liked, disliked, or no reaction)."
    ),
    responses={
        200: {"description": "Movie reaction summary retrieved successfully"},
        401: {"description": "Unauthorized - invalid or missing token"},
        404: {"description": "Not Found - movie does not exist"},
    },
    status_code=status.HTTP_200_OK
)
async def get_movie_reactions(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)],
):
    return await service.get_movie_reactions(
        user_id=user.id, movie_id=movie_id
    )


@router.post(
    "/{movie_id}/rating",
    response_model=MovieRatingSummarySchema,
    summary="Rate a movie on a 1-10 scale",
    description=(
        "Rate a movie on a scale from 1 to 10. If the user has already rated "
        "the movie, this action will update their existing rating."
    ),
    responses={
        200: {"description": "Movie rated successfully"},
        401: {"description": "Unauthorized - invalid or missing token"},
        404: {"description": "Not Found - movie does not exist"},
        422: {
            "description": (
                "Unprocessable Entity - invalid rating value (must be 1-10)"
            )                
        },
    },
    status_code=status.HTTP_200_OK
)
@limiter.limit("10/minute")
async def rate_movie(
    movie_id: int,
    payload: MovieRatingCreateSchema,
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)],
):
    return await service.rate_movie(
        user_id=user.id,
        movie_id=movie_id,
        payload=payload
    )


@router.delete(
    "/{movie_id}/rating",
    response_model=MovieRatingSummarySchema,
    summary="Remove user rating for a movie",
    description=(
        "Remove the user's rating for a specific movie. If the user has not "
        "rated the movie, this action will have no effect."
    ),
    responses={
        200: {"description": "Movie rating removed successfully"},
        401: {"description": "Unauthorized - invalid or missing token"},
        404: {"description": "Not Found - movie does not exist"},
    },
    status_code=status.HTTP_200_OK
)
async def delete_movie_rating(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)],
):
    return await service.delete_movie_rating(
        user_id=user.id,
        movie_id=movie_id
    )


@router.get(
    "/{movie_id}/rating",
    response_model=MovieRatingSummarySchema,
    summary="Get rating summary for a movie",
    description=(
        "Retrieve a summary of ratings for a specific movie, including the "
        "average rating, total number of ratings, and the current user's "
        "rating (if any)."
    ),
    responses={
        200: {"description": "Movie rating summary retrieved successfully"},
        401: {"description": "Unauthorized - invalid or missing token"},
        404: {"description": "Not Found - movie does not exist"},
    },
    status_code=status.HTTP_200_OK
)
async def get_movie_rating_summary(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)],
):
    return await service.get_movie_rating_summary(
        user_id=user.id,
        movie_id=movie_id
    )


@router.post(
    "/{movie_id}/favorite",
    response_model=FavoriteMovieResponseSchema,
    summary="Add movie to favorites",
    description=(
        "Add a movie to the user's list of favorite movies. If the movie is "
        "already in the user's favorites, this action will have no effect."
    ),
    responses={
        200: {"description": "Movie added to favorites successfully"},
        401: {"description": "Unauthorized - invalid or missing token"},
        404: {"description": "Not Found - movie does not exist"},
    },
    status_code=status.HTTP_200_OK
)
@limiter.limit("20/minute")
async def add_to_favorites(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)]
):
    return await service.add_to_favorites(user.id, movie_id)


@router.delete(
    "/{movie_id}/favorite",
    response_model=FavoriteMovieResponseSchema,
    summary="Remove movie from favorites",
    description=(
        "Remove a movie from the user's list of favorite movies. If the movie "
        "is not in the user's favorites, this action will have no effect."
    ),
    responses={
        200: {"description": "Movie removed from favorites successfully"},
        401: {"description": "Unauthorized - invalid or missing token"},
        404: {"description": "Not Found - movie does not exist"},
    },
    status_code=status.HTTP_200_OK
)
async def remove_from_favorites(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)]
):
    return await service.remove_from_favorites(user.id, movie_id)


@router.post(
    "/{movie_id}/comments",
    response_model=CommentSchema,
    summary="Add a comment to a movie",
    description=(
        "Add a comment to a specific movie. The comment will be associated "
        "with the current user as the author. If the movie does not exist, "
        "a 404 error will be returned. If a parent comment ID is provided, "
        "it must belong to the same movie; otherwise, a 400 error "
        "will be returned."
    ),
    responses={
        201: {"description": "Comment added successfully"},
        400: {
            "description": (
                "Bad Request - invalid parent comment ID or other input data"
            )
        },
        401: {"description": "Unauthorized - invalid or missing token"},
        404: {"description": "Not Found - movie does not exist"},
    },
    status_code=status.HTTP_201_CREATED
)
@limiter.limit("10/minute")
async def add_comment(
    movie_id: int,
    payload: CommentCreateSchema,
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)]
):
    return await service.add_comment(movie_id, user.id, payload)


@router.get(
    "/{movie_id}/comments",
    response_model=list[CommentSchema],
    summary="List comments for a movie",
    description=(
        "Retrieve a list of comments for a specific movie. Each comment "
        "includes the author's ID and the comment text."
    ),
    responses={
        200: {"description": "Comments retrieved successfully"},
        404: {"description": "Not Found - movie does not exist"},
    },
    status_code=status.HTTP_200_OK
)
async def list_comments(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)]
):
    return await service.list_comments(movie_id)
