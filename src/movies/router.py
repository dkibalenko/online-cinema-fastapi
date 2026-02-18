from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from movies.dependencies import get_movie_service
from movies.schemas import (
    MovieCreateSchema,
    MovieDetailSchema,
    MovieListItemSchema,
    MovieUpdateSchema,
    MovieFilterParams,
    MovieSortParams,
    MovieReactionActionResponseSchema,
    MovieReactionSummarySchema
)
from movies.exceptions import MovieNotFoundError
from movies.filters import build_movie_filter_query
from movies.service import MovieService
from auth.dependencies import get_current_user
from auth.models import User


router = APIRouter(prefix="/movies", tags=["movies"])


@router.get(
    "",
    response_model=Page[MovieListItemSchema],
    summary="List Movies",
    status_code=status.HTTP_200_OK
)
async def list_movies(
    filter_query: Annotated[MovieFilterParams, Depends()],
    sort_query: Annotated[MovieSortParams, Depends()],
    service: Annotated[MovieService, Depends(get_movie_service)]
) -> Page[MovieListItemSchema]:
    stmt = build_movie_filter_query(filter_query, sort_query)
    return await paginate(service.repo.db, stmt)


@router.get(
    "/{movie_id}",
    response_model=MovieDetailSchema,
    summary="Get Movie",
    status_code=status.HTTP_200_OK
)
async def get_movie(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)]
) -> MovieDetailSchema:
    try:
        return await service.get_movie_detail(movie_id)
    except MovieNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
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
    try:
        return await service.update_movie(movie_id, data)
    except MovieNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete(
    "/{movie_id}",
    summary="Delete Movie",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_movie(
    movie_id: int,
    service: Annotated[MovieService, Depends(get_movie_service)]
):
    try:
        await service.delete_movie(movie_id)
    except MovieNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


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
