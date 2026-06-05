import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseSchema(BaseModel):
    # initialize a model from a database object instead of just a dictionary
    model_config = ConfigDict(from_attributes=True)


class CertificationSchema(BaseSchema):
    name: str


class GenreSchema(BaseSchema):
    name: str


class StarSchema(BaseSchema):
    name: str


class DirectorSchema(BaseSchema):
    name: str


class MovieBaseSchema(BaseModel):
    name: str = Field(..., max_length=255)
    year: int = Field(..., ge=1900, le=2026, description="Release year")
    time: int = Field(..., description="Duration in minutes")
    imdb: float = Field(..., ge=0, le=10)
    votes: int = Field(..., ge=0, description="Number of votes on IMDb")
    description: str

    meta_score: float | None = Field(None, ge=0, le=100)
    gross: Decimal | None = Field(None, decimal_places=2)
    price: Decimal | None = Field(Decimal("0.00"), decimal_places=2)


class MovieListItemSchema(BaseSchema):
    id: int
    name: str
    year: int
    imdb: float
    description: str
    is_favorite: bool = False


class MovieDetailSchema(MovieBaseSchema):
    id: int
    uu_id: uuid.UUID
    certification: CertificationSchema
    genres: list[GenreSchema]
    stars: list[StarSchema]
    directors: list[DirectorSchema]
    is_favorite: bool = False

    model_config = ConfigDict(from_attributes=True)


class MovieCreateSchema(MovieBaseSchema):
    certification: str
    genres: list[str] = Field(default_factory=list)
    stars: list[str] = Field(default_factory=list)
    directors: list[str] = Field(default_factory=list)

    @field_validator("certification", mode="before")
    @classmethod
    def normalize_certification(cls, value: str) -> str:
        """Normalize the certification field.

        Strip leading/trailing whitespace and convert to uppercase if
        the input is a string.

        Args:
            value (str): The certification string to normalize.

        Returns:
            str: The normalized certification string.
        """
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("genres", "stars", "directors", mode="before")
    @classmethod
    def normalize_list_fields(cls, values: list[str]) -> list[str]:
        """Normalize a list of strings.

        Convert to title case and strip leading/trailing whitespace.

        If the input is not a list, return the input as is.

        Args:
            values (list[str]): The list of strings to normalize.

        Returns:
            list[str]: The normalized list of strings.
        """
        if not isinstance(values, list):
            return values
        return [
            value.strip().title() for value in values if isinstance(value, str)
        ]


class MovieUpdateSchema(BaseModel):
    name: str | None = Field(None, max_length=255)
    year: int | None = Field(None, ge=1900, le=2026)
    time: int | None = Field(None, description="Duration in minutes")
    imdb: float | None = Field(None, ge=0, le=10)
    votes: int | None = Field(None, ge=0)
    description: str | None = None
    meta_score: float | None = Field(None, ge=0, le=100)
    gross: Decimal | None = Field(None, decimal_places=2)
    price: Decimal | None = Field(None, decimal_places=2)


class GenreWithCountSchema(BaseSchema):
    id: int
    name: str
    movie_count: int


class MovieFilterParams(BaseModel):
    genre_id: int | None = Field(None, description="Filter movies by genre ID")
    search: str | None = Field(
        None, description="Search by title, description, star, or director"
    )
    year: int | None = Field(None, description="Filter by year")
    min_imdb: float | None = Field(
        None, description="Filter by minimum IMDb rating"
    )
    min_price: float | None = Field(
        None, description="Filter by minimum price"
    )
    max_price: float | None = Field(
        None, description="Filter by maximum price"
    )


class MovieSortParams(BaseModel):
    sort_by: str = Field(
        "id",
        pattern="^(id|name|year|imdb|votes|price)$",
        description="Field to sort by",
    )
    order: str = Field(
        "desc", pattern="^(asc|desc)$", description="Sort order: asc or desc"
    )


class MovieReactionSummarySchema(BaseSchema):
    movie_id: int
    likes: int
    dislikes: int
    user_reaction: str | None  # "like" | "dislike" | None


class MovieReactionActionResponseSchema(BaseSchema):
    movie_id: int
    action: str  # "like" | "dislike" | "removed"
    likes: int
    dislikes: int
    user_reaction: str | None


class MovieRatingCreateSchema(BaseModel):
    rating: int = Field(ge=1, le=10)


class MovieRatingSummarySchema(BaseSchema):
    movie_id: int
    average_rating: float | None
    ratings_count: int
    user_rating: int | None


class FavoriteMovieResponseSchema(BaseSchema):
    movie_id: int
    is_favorite: bool


class FavoriteMovieListSchema(MovieListItemSchema):
    is_favorite: bool = True


class CommentCreateSchema(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: int | None = None


class CommentSchema(BaseSchema):
    id: int
    movie_id: int
    user_id: int
    content: str
    parent_id: int | None
    created_at: datetime
    updated_at: datetime
