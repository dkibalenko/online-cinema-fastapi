from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field

from schemas.movies import MovieCreateSchema, MovieListItemSchema, MovieDetailSchema, MovieUpdateSchema
from database import get_db, Movie
from database.models.movies import Certification, Genre, Star, Director
from routes.utils import get_or_create_related


router = APIRouter()


class MovieFilterParams(BaseModel):
    year: Optional[int] = Field(None, description="Filter by year")
    min_imdb: Optional[float] = Field(
        None, description="Filter by minimum IMDb rating"
    )
    min_price: Optional[float] = Field(
        None, description="Filter by minimum price"
    )
    max_price: Optional[float] = Field(
        None, description="Filter by maximum price"
    )


class MovieSortParams(BaseModel):
    sort_by: Optional[str] = Field(
        "id",
        pattern="^(id|name|year|imdb|votes|price)$",
        description="Field to sort by"
    )
    order: Optional[str] = Field(
        "desc",
        pattern="^(asc|desc)$",
        description="Sort order: asc or desc"
    )


@router.get(
    "/movies/",
    response_model=Page[MovieListItemSchema],
    status_code=status.HTTP_200_OK
)
async def get_movie_list(
    filter_query: MovieFilterParams = Depends(),
    sort_query: MovieSortParams = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Page[MovieListItemSchema]:
    """
    Fetches a list of movies with pagination.

    Parameters:
    - filter_query: FilterParams - filter by year, minimum IMDb rating, 
        minimum price, maximum price
    - sort_query: SortParams - sort by id, name, year, IMDb rating, votes, 
        price, with an option to sort in ascending or descending order

    Returns:
    - Page[MovieListItemSchema] - a paginated list of movies
    """
    stmt = select(Movie)

    # 1. Apply Filtering
    if filter_query.year is not None:
        stmt = stmt.where(Movie.year == filter_query.year)

    if filter_query.min_imdb is not None:
        stmt = stmt.where(Movie.imdb >= filter_query.min_imdb)

    if filter_query.min_price is not None:
        stmt = stmt.where(Movie.price >= filter_query.min_price)

    if filter_query.max_price is not None:
        stmt = stmt.where(Movie.price <= filter_query.max_price)

    # 2. Apply Sorting
    sort_column = getattr(Movie, sort_query.sort_by)

    if sort_query.order == "desc":
        stmt = stmt.order_by(sort_column.desc())
    else:
        stmt = stmt.order_by(sort_column.asc())

    return await paginate(db, stmt)


@router.get(
    "/movies/{movie_id}/", 
    response_model=MovieDetailSchema,
    status_code=status.HTTP_200_OK
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


@router.post(
    "/movies/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_201_CREATED
)
async def create_movie(
    movie_data: MovieCreateSchema,
    db: AsyncSession = Depends(get_db)
) -> MovieDetailSchema:
    """
    Creates a new movie.
    Checks for existing movie with the same name and year.
    Handles many-to-many collections efficiently using get_or_create_related.
    Raises HTTPException with 409_CONFLICT if the movie already exists.
    Raises HTTPException with 400_BAD_REQUEST if there is an integrity error.
    """
    
    existing_stmt = select(Movie).where(
        (Movie.name == movie_data.name),
        (Movie.year == movie_data.year)
    )
    # 1. Check for existing movie
    existing_result = await db.execute(existing_stmt)
    existing_movie = existing_result.scalar_one_or_none()

    if existing_movie:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Movie with the name '{movie_data.name}' and year "
            f"'{movie_data.year}' already exists."
        )

    try:
        # 2. Handle Certification (Get or Create)
        certs = await get_or_create_related(
            Certification, [movie_data.certification], db
        )
        certification = certs[0]

        # 3. Resolve Many-to-Many Collections efficiently
        genres = await get_or_create_related(Genre, movie_data.genres, db)
        stars = await get_or_create_related(Star, movie_data.stars, db)
        directors = await get_or_create_related(
            Director, movie_data.directors, db
        )

        # 4. Create Movie
        # exclude the relation fields from the dict and pass resolved objects
        movie_dict = movie_data.model_dump(  # gives a dict of validated data
            exclude={"genres", "stars", "directors", "certification"}
        )
        new_movie = Movie(
            **movie_dict,
            certification=certification,
            genres=genres,
            stars=stars,
            directors=directors
        )
        db.add(new_movie)
        await db.commit()

        # Refresh with joined/selectin data for the response
        await db.refresh(
            new_movie,
            ["certification","genres", "stars", "directors"]
        )

        return new_movie
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integrity error. Ensure all related data is valid."
        )


@router.patch(
    "/movies/{movie_id}/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_200_OK
)
async def update_movie(
    movie_id: int,
    movie_data: MovieUpdateSchema,
    db: AsyncSession = Depends(get_db),
) -> MovieDetailSchema:
    """
    Updates a movie by ID.

    Raises HTTPException with 404_NOT_FOUND if the movie doesn't exist.
    Raises HTTPException with 400_BAD_REQUEST if no fields are provided for update.
    Raises HTTPException with 400_BAD_REQUEST if integrity error occurs on update.
    """
    stmt = (select(Movie).where(Movie.id == movie_id))
    result = await db.execute(stmt)
    movie = result.unique().scalar_one_or_none()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with ID {movie_id} not found."
        )
    
    # Extract only the fields sent in the request
    update_data = movie_data.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update."
        )

    # Apply changes
    for field, value in update_data.items():
        setattr(movie, field, value)

    try:
        await db.commit()
        # Refresh to get any server-side computed values
        await db.refresh(
            movie, ["certification", "genres", "stars", "directors"]
        )
        return movie
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integrity error. Ensure values are unique/valid."
        )


@router.delete(
    "/movies/{movie_id}/",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes a movie by ID.

    Raises HTTPException with 404_NOT_FOUND if the movie doesn't exist.
    """
    movie = await db.get(Movie, movie_id)

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with ID {movie_id} not found."
        )

    await db.delete(movie)
    await db.commit()
