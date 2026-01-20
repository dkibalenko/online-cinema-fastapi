from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.genres import GenreWithCountSchema
from database.models.movies import Genre, MoviesGenresModel


router = APIRouter()


@router.get("/", response_model=List[GenreWithCountSchema])
async def get_genre_list_with_count(db: AsyncSession = Depends(get_db)):
    """
    Returns all genres along with the count of movies associated with each.
    """
    # SQL logic: 
    # SELECT genres.id, genres.name, count(movie_genres.movie_id) 
    # FROM genres LEFT JOIN movie_genres ON genres.id = movie_genres.genre_id 
    # GROUP BY genres.id
    stmt = (
        select(
            Genre.id,
            Genre.name,
            func.count(MoviesGenresModel.c.movie_id).label("movie_count")
        )
        .outerjoin(MoviesGenresModel, Genre.id == MoviesGenresModel.c.genre_id)
        .group_by(Genre.id, Genre.name)
        .order_by(func.count(MoviesGenresModel.c.movie_id).desc())
    )

    result = await db.execute(stmt)
    # Mapping raw rows to our schema
    return [
        {"id": row.id, "name": row.name, "movie_count": row.movie_count} 
        for row in result.all()
    ]
