from decimal import Decimal
from typing import List, Optional
import uuid

from pydantic import BaseModel, Field, field_validator


class CertificationSchema(BaseModel):
    name: str

    model_config = {"from_attributes": True}


class GenreSchema(BaseModel):
    name: str

    model_config = {"from_attributes": True}


class StarSchema(BaseModel):
    name: str

    model_config = {"from_attributes": True}


class DirectorSchema(BaseModel):
    name: str

    model_config = {"from_attributes": True}


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

    model_config = {"from_attributes": True}


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    year: int
    imdb: float
    description: str

    model_config = {"from_attributes": True}


class MovieDetailSchema(MovieBaseSchema):
    id: int
    uu_id: uuid.UUID
    certification: CertificationSchema
    genres: List[GenreSchema]
    stars: List[StarSchema]
    directors: List[DirectorSchema]

    model_config = {"from_attributes": True}


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

    model_config = {"from_attributes": True}
