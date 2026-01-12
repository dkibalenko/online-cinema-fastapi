from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from schemas.movies import MovieListItemSchema, MovieDetailSchema
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


@router.get(
    "/movies/{movie_id}/", 
    response_model=MovieDetailSchema
)
async def get_movie_detail(
    movie_id: int,
    db: AsyncSession = Depends(get_db)
) -> MovieDetailSchema:
    """
    Fetch a single movie by ID with all related entities.
    Uses joinedload for M:1 and selectinload for M:M relationships.
    """
    stmt = (
        select(Movie)
        .options(
            joinedload(Movie.certification),
            selectinload(Movie.genres),
            selectinload(Movie.directors),
            selectinload(Movie.stars)
        )
        .where(Movie.id == movie_id)
    )

    result = await db.execute(stmt)
    movie = result.unique().scalar_one_or_none()

    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with ID {movie_id} not found."
        )

    # FastAPI handles model_validate automatically because 
    # response_model is set and from_attributes=True is set in the config
    return movie
