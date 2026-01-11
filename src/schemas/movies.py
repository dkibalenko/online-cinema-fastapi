from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel, Field


class MovieBaseSchema(BaseModel):
    name: str = Field(..., max_length=255)
    year: int
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
