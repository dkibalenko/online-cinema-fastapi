from database.models.base import Base

from database.models.movies import (
    Movie,
    Certification,
    Director,
    Genre,
    Star,
    MoviesDirectorsModel,
    MoviesGenresModel,
    MoviesStarsModel
)

from database.session_postgres import (
    get_postgresql_db as get_db,
    get_postgresql_db_contexmanager as get_db_contextmanager
)
