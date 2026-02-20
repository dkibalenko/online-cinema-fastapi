from __future__ import annotations
import uuid
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    Integer,
    Float,
    Text,
    Numeric,
    ForeignKey,
    UniqueConstraint,
    Table,
    Column,
    DateTime,
    Boolean
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func

from database import Base


MoviesGenresModel = Table(
    "movie_genres",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    ),
    Column(
        "genre_id",
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    ),
)

MoviesStarsModel = Table(
    "movie_stars",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    ),
    Column(
        "star_id",
        ForeignKey("stars.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    ),
)

MoviesDirectorsModel = Table(
    "movie_directors",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    ),
    Column(
        "director_id",
        ForeignKey("directors.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False
    ),
)


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie",
        secondary=MoviesGenresModel,
        back_populates="genres"
    )

    def __repr__(self):
        return f"<Genre(name='{self.name}')>"


class Star(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie",
        secondary=MoviesStarsModel,
        back_populates="stars"
    )

    def __repr__(self):
        return f"<Star(name='{self.name}')>"


class Director(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie",
        secondary=MoviesDirectorsModel,
        back_populates="directors"
    )

    def __repr__(self):
        return f"<Director(name='{self.name}')>"


class Movie(Base):
    __tablename__ = "movies"
    __table_args__ = (
        UniqueConstraint(
            "name", "year", "time", name="unique_movie_constraint"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uu_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        server_default=func.gen_random_uuid(), # Postgres generate the UUID
        unique=True,
        index=True,
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[Optional[float]] = mapped_column(Float)
    gross: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00")
    )
    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id", ondelete="RESTRICT"),
        nullable=False
    )
    certification: Mapped["Certification"] = relationship(
        "Certification",
        back_populates="movies"
    )
    genres: Mapped[list["Genre"]] = relationship(
        "Genre",
        secondary=MoviesGenresModel,
        back_populates="movies"
    )
    stars: Mapped[list["Star"]] = relationship(
        "Star",
        secondary=MoviesStarsModel,
        back_populates="movies"
    )
    directors: Mapped[list["Director"]] = relationship(
        "Director",
        secondary=MoviesDirectorsModel,
        back_populates="movies"
    )
    likes: Mapped[list["MovieLike"]] = relationship(
        "MovieLike",
        back_populates="movie",
        cascade="all, delete-orphan"
    )

    @classmethod
    def default_order_by(cls):
        return [cls.id.desc()]

    def __repr__(self):
        return f"Movie(name={self.name}, year={self.year}, imdb={self.imdb})"


class MovieLike(Base):
    __tablename__ = "movie_likes"
    __table_args__ = (
        UniqueConstraint(
            "user_id", 
            "movie_id",
            name="uq_movie_like_user_movie"
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),  # user is deleted → all their likes are deleted
        primary_key=True
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),  # movie is deleted → all likes for that movie are deleted
        primary_key=True
    )
    is_like: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    movie: Mapped["Movie"] = relationship("Movie", back_populates="likes")
    user: Mapped["User"] = relationship("User", back_populates="movie_likes")


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    movies: Mapped[List["Movie"]] = relationship(
        back_populates="certification"
    )

    def __repr__(self):
        return f"Certification(name={self.name})"
