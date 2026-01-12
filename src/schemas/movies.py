from decimal import Decimal
from typing import List, Optional
import uuid

from pydantic import BaseModel, Field


class CertificationSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class GenreSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class StarSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class DirectorSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class MovieBaseSchema(BaseModel):
    name: str = Field(..., max_length=255)
    year: int = Field(..., ge=1900, le=2026)
    time: int
    imdb: float = Field(..., ge=0, le=10)
    votes: int
    meta_score: Optional[float]
    gross: Optional[Decimal]
    description: str
    price: Optional[Decimal]

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
