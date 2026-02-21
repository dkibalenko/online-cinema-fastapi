from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi_pagination import Page

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
    FavoriteMovieListSchema
)
from movies.service import MovieService
from auth.dependencies import get_current_user
from users.models import User


router = APIRouter(prefix="/movies", tags=["movies"])


# static endpoints must be placed above any {movie_id} routes
@router.get(
    "",
    response_model=Page[MovieListItemSchema],
    summary="List Movies",
    status_code=status.HTTP_200_OK
)
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
    response_model=MovieDetailSchema,
    summary="Create Movie",
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
    status_code=status.HTTP_200_OK
)
async def get_movie(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)]
) -> MovieDetailSchema:
    return await service.get_movie_detail(movie_id, user.id)


@router.patch(
    "/{movie_id}",
    summary="Update Movie",
    response_model=MovieDetailSchema,
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
    summary="Delete Movie",
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
    status_code=status.HTTP_200_OK,
)
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
    status_code=status.HTTP_200_OK,
)
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
    status_code=status.HTTP_200_OK
)
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
    status_code=status.HTTP_200_OK
)
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
    status_code=status.HTTP_200_OK
)
async def remove_from_favorites(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)],
    user: Annotated[User, Depends(get_current_user)]
):
    return await service.remove_from_favorites(user.id, movie_id)
