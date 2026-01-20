from pydantic import BaseModel


class GenreWithCountSchema(BaseModel):
    id: int
    name: str
    movie_count: int

    class Config:
        from_attributes = True
