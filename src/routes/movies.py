from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from schemas.movies import MovieListItemSchema
from database import get_db, Movie


router = APIRouter()


@router.get(
    "/movies/",
    response_model=Page[MovieListItemSchema]
)
async def get_movie_list(
    db: AsyncSession = Depends(get_db)
) -> Page[MovieListItemSchema]:
    """
    Returns a paginated list of movies. 
    fastapi-pagination handles the 'Page' wrapper and SQL execution.
    """
    stmt = select(Movie).order_by(Movie.id.desc())

    return await paginate(db, stmt)
