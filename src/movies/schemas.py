from decimal import Decimal
from typing import List, Optional
import uuid

from pydantic import BaseModel, Field, field_validator, ConfigDict


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

    meta_score: Optional[float] = Field(None, ge=0, le=100)
    gross: Optional[Decimal] = Field(None, decimal_places=2)
    price: Optional[Decimal] = Field(Decimal("0.00"), decimal_places=2)


class MovieListItemSchema(BaseSchema):
    id: int
    name: str
    year: int
    imdb: float
    description: str


class MovieDetailSchema(MovieBaseSchema):
    id: int
    uu_id: uuid.UUID
    certification: CertificationSchema
    genres: List[GenreSchema]
    stars: List[StarSchema]
    directors: List[DirectorSchema]

    model_config = ConfigDict(from_attributes=True)


class MovieCreateSchema(MovieBaseSchema):
    certification: str
    genres: List[str] = Field(default_factory=list)
    stars: List[str] = Field(default_factory=list)
    directors: List[str] = Field(default_factory=list)

    @field_validator("certification", mode="before")
    @classmethod
    def normalize_certification(cls, value: str) -> str:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("genres", "stars", "directors", mode="before")
    @classmethod
    def normalize_list_fields(cls, values: List[str]) -> List[str]:
        if not isinstance(values, list):
            return values
        return [
            value.strip().title() for value in values if isinstance(value, str)
        ]


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    year: Optional[int] = Field(None, ge=1900, le=2026)
    time: Optional[int] = Field(None, description="Duration in minutes")
    imdb: Optional[float] = Field(None, ge=0, le=10)
    votes: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    meta_score: Optional[float] = Field(None, ge=0, le=100)
    gross: Optional[Decimal] = Field(None, decimal_places=2)
    price: Optional[Decimal] = Field(None, decimal_places=2)


class GenreWithCountSchema(BaseSchema):
    id: int
    name: str
    movie_count: int


class MovieFilterParams(BaseModel):
    genre_id: Optional[int] = Field(
        None,
        description="Filter movies by genre ID"
    )
    search: Optional[str] = Field(
        None, description="Search by title, description, star, or director"
    )
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
