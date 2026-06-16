from typing import Annotated

from fastapi import APIRouter, Depends, status

from movies.dependencies import get_movie_service
from movies.schemas import GenreWithCountSchema
from movies.services import MovieService

router = APIRouter(prefix="/genres", tags=["Genres"])


@router.get(
    "",
    response_model=list[GenreWithCountSchema],
    summary="List genres with movie count",
    description="Retrieve a list of genres with their associated movie count.",
    responses={200: {"description": "List of genres retrieved successfully"}},
    status_code=status.HTTP_200_OK,
)
async def get_genre_list_with_count(
    service: Annotated[MovieService, Depends(get_movie_service)],
) -> list[GenreWithCountSchema]:
    """Retrieve a list of genres with their associated movie count."""
    return await service.list_genres_with_count()
