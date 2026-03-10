from sqlalchemy import Select, or_, select

from movies.models import Director, Movie, MoviesGenresModel, Star
from movies.schemas import MovieFilterParams, MovieSortParams


def build_movie_filter_query(
    filter_query: MovieFilterParams,
    sort_query: MovieSortParams,
    base_query: Select | None = None,
) -> Select:
    """Builds a SQLAlchemy select statement for filtering and sorting movies.

    Args:
        filter_query (MovieFilterParams): The filter options.
        sort_query (MovieSortParams): The sorting options.
        base_query (Select, optional): A base query to build upon.
            Defaults to None.

    Returns:
        Select: The SQLAlchemy select statement.
    """
    # base query. ensures that joins (stars, directors) don’t duplicate rows
    stmt = base_query if base_query is not None else select(Movie)
    stmt = stmt.distinct()

    # 1. Apply Genre Filter (/movies?genre_id=3. Clicking on a genre)
    if filter_query.genre_id:
        stmt = stmt.join(MoviesGenresModel).where(
            MoviesGenresModel.c.genre_id == filter_query.genre_id
        )

    # 2. Apply Search
    if filter_query.search:
        term = f"%{filter_query.search}%"

        # join relationships needed for searching
        # use outerjoin so we don't exclude movies that have no stars/directors
        stmt = (
            stmt.outerjoin(Movie.stars)
            .outerjoin(Movie.directors)
            .where(
                or_(
                    Movie.name.ilike(term),
                    Movie.description.ilike(term),
                    Star.name.ilike(term),
                    Director.name.ilike(term),
                )
            )
        )

    # 3. Apply Filtering (/movies?sort_by=imdb&order=asc)
    if filter_query.year:
        stmt = stmt.where(Movie.year == filter_query.year)

    if filter_query.min_imdb:
        stmt = stmt.where(Movie.imdb >= filter_query.min_imdb)

    if filter_query.min_price:
        stmt = stmt.where(Movie.price >= filter_query.min_price)

    if filter_query.max_price:
        stmt = stmt.where(Movie.price <= filter_query.max_price)

    # 4. Apply Sorting
    sort_col = getattr(Movie, sort_query.sort_by)

    return stmt.order_by(
        sort_col.desc() if sort_query.order == "desc" else sort_col.asc()
    )
