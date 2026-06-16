from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi_pagination import Page

from auth.dependencies import get_current_user
from movies.dependencies import (
    get_movie_comment_service,
    get_movie_reaction_service,
)
from movies.schemas import (
    CommentCreateSchema,
    CommentSchema,
    FavoriteMovieResponseSchema,
    MovieRatingCreateSchema,
    MovieRatingSummarySchema,
    MovieReactionActionResponseSchema,
    MovieReactionSummarySchema,
)
from movies.services import MovieCommentService, MovieReactionService
from rate_limiting import limiter
from users.models import User

router = APIRouter(prefix="/movies", tags=["Movie Interactions"])


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
    request: Request,
    movie_id: int,
    service: Annotated[
        MovieReactionService, Depends(get_movie_reaction_service)
    ],
    user: Annotated[User, Depends(get_current_user)],
) -> MovieReactionActionResponseSchema:
    """Like a movie."""
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
    request: Request,
    movie_id: int,
    service: Annotated[
        MovieReactionService, Depends(get_movie_reaction_service)
    ],
    user: Annotated[User, Depends(get_current_user)],
) -> MovieReactionActionResponseSchema:
    """Dislike a movie."""
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
    service: Annotated[
        MovieReactionService, Depends(get_movie_reaction_service)
    ],
    user: Annotated[User, Depends(get_current_user)],
) -> MovieReactionActionResponseSchema:
    """Remove user's like or dislike from a movie."""
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
    status_code=status.HTTP_200_OK,
)
async def get_movie_reactions(
    movie_id: int,
    service: Annotated[
        MovieReactionService, Depends(get_movie_reaction_service)
    ],
    user: Annotated[User, Depends(get_current_user)],
):
    """Retrieve a summary of reactions for a specific movie."""
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
    status_code=status.HTTP_200_OK,
)
@limiter.limit("10/minute")
async def rate_movie(
    request: Request,
    movie_id: int,
    payload: MovieRatingCreateSchema,
    service: Annotated[
        MovieReactionService, Depends(get_movie_reaction_service)
    ],
    user: Annotated[User, Depends(get_current_user)],
):
    """Rate a movie on a scale from 1 to 10."""
    return await service.rate_movie(
        user_id=user.id, movie_id=movie_id, payload=payload
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
    status_code=status.HTTP_200_OK,
)
async def delete_movie_rating(
    movie_id: int,
    service: Annotated[
        MovieReactionService, Depends(get_movie_reaction_service)
    ],
    user: Annotated[User, Depends(get_current_user)],
):
    """Remove the user's rating for a specific movie."""
    return await service.delete_movie_rating(
        user_id=user.id, movie_id=movie_id
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
    status_code=status.HTTP_200_OK,
)
async def get_movie_rating_summary(
    movie_id: int,
    service: Annotated[
        MovieReactionService, Depends(get_movie_reaction_service)
    ],
    user: Annotated[User, Depends(get_current_user)],
):
    """Retrieve a summary of ratings for a specific movie."""
    return await service.get_movie_rating_summary(
        user_id=user.id, movie_id=movie_id
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
    status_code=status.HTTP_200_OK,
)
@limiter.limit("20/minute")
async def add_to_favorites(
    request: Request,
    movie_id: int,
    service: Annotated[
        MovieReactionService, Depends(get_movie_reaction_service)
    ],
    user: Annotated[User, Depends(get_current_user)],
):
    """Add a movie to the user's list of favorite movies."""
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
    status_code=status.HTTP_200_OK,
)
async def remove_from_favorites(
    movie_id: int,
    service: Annotated[
        MovieReactionService, Depends(get_movie_reaction_service)
    ],
    user: Annotated[User, Depends(get_current_user)],
):
    """Remove a movie from the user's list of favorite movies."""
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
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def add_comment(
    request: Request,
    movie_id: int,
    payload: CommentCreateSchema,
    service: Annotated[
        MovieCommentService, Depends(get_movie_comment_service)
    ],
    user: Annotated[User, Depends(get_current_user)],
):
    """Add a comment to a specific movie."""
    return await service.add_comment(movie_id, user.id, payload)


@router.get(
    "/{movie_id}/comments",
    response_model=Page[CommentSchema],
    summary="List comments for a movie",
    description=(
        "Retrieve a paginated list of comments for a specific movie. Each "
        "comment includes the author's ID and the comment text."
    ),
    responses={
        200: {"description": "Comments retrieved successfully"},
        404: {"description": "Not Found - movie does not exist"},
    },
    status_code=status.HTTP_200_OK,
)
async def list_comments(
    movie_id: int,
    service: Annotated[
        MovieCommentService, Depends(get_movie_comment_service)
    ],
):
    """Retrieve a paginated list of comments for a specific movie."""
    return await service.list_comments(movie_id)
