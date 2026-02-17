from typing import List, Annotated

from fastapi import APIRouter, Depends, status

from movies.schemas import GenreWithCountSchema
from movies.service import MovieService
from movies.dependencies import get_movie_service


router = APIRouter(prefix="/genres", tags=["genres"])


@router.get(
    "/",
    response_model=List[GenreWithCountSchema],
    summary="List genres with movie count",
    status_code=status.HTTP_200_OK
)
async def get_genre_list_with_count(
    service: Annotated[MovieService, Depends(get_movie_service)]
) -> List[GenreWithCountSchema]:
    return await service.list_genres_with_count()
