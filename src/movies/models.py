from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base

if TYPE_CHECKING:
    from users.models import User


MoviesGenresModel = Table(
    "movie_genres",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "genre_id",
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)

MoviesStarsModel = Table(
    "movie_stars",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "star_id",
        ForeignKey("stars.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)

MoviesDirectorsModel = Table(
    "movie_directors",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "director_id",
        ForeignKey("directors.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list[Movie]] = relationship(
        "Movie", secondary=MoviesGenresModel, back_populates="genres"
    )

    def __repr__(self):
        return f"<Genre(name='{self.name}')>"


class Star(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list[Movie]] = relationship(
        "Movie", secondary=MoviesStarsModel, back_populates="stars"
    )

    def __repr__(self):
        return f"<Star(name='{self.name}')>"


class Director(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list[Movie]] = relationship(
        "Movie", secondary=MoviesDirectorsModel, back_populates="directors"
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
        server_default=func.gen_random_uuid(),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[float | None] = mapped_column(Float)
    gross: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00")
    )
    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id", ondelete="RESTRICT"), nullable=False
    )
    certification: Mapped[Certification] = relationship(
        "Certification", back_populates="movies"
    )
    genres: Mapped[list[Genre]] = relationship(
        "Genre", secondary=MoviesGenresModel, back_populates="movies"
    )
    stars: Mapped[list[Star]] = relationship(
        "Star", secondary=MoviesStarsModel, back_populates="movies"
    )
    directors: Mapped[list[Director]] = relationship(
        "Director", secondary=MoviesDirectorsModel, back_populates="movies"
    )
    likes: Mapped[list[MovieLike]] = relationship(
        "MovieLike", back_populates="movie", cascade="all, delete-orphan"
    )
    ratings: Mapped[list[MovieRating]] = relationship(
        "MovieRating", back_populates="movie", cascade="all, delete-orphan"
    )
    favorites: Mapped[list[FavoriteMovie]] = relationship(
        "FavoriteMovie", back_populates="movie", cascade="all, delete-orphan"
    )
    comments: Mapped[list[MovieComment]] = relationship(
        "MovieComment", back_populates="movie", cascade="all, delete-orphan"
    )
    video: Mapped[VideoFile | None] = relationship(
        "VideoFile",
        back_populates="movie",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @classmethod
    def default_order_by(cls):
        """Returns a default ordering for the model, if applicable."""
        return [cls.id.desc()]

    def __repr__(self):
        return f"Movie(name={self.name}, year={self.year}, imdb={self.imdb})"


class MovieLike(Base):
    __tablename__ = "movie_likes"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "movie_id", name="uq_movie_like_user_movie"
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id", ondelete="CASCADE"
        ),  # user is deleted → all their likes are deleted
        primary_key=True,
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey(
            "movies.id", ondelete="CASCADE"
        ),  # movie is deleted → all likes for that movie are deleted
        primary_key=True,
    )
    is_like: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    movie: Mapped[Movie] = relationship("Movie", back_populates="likes")
    user: Mapped[User] = relationship("User", back_populates="movie_likes")

    def __repr__(self):
        return (
            f"MovieLike(user_id={self.user_id}, movie_id={self.movie_id}, "
            f"is_like={self.is_like})"
        )


class MovieRating(Base):
    __tablename__ = "movie_ratings"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "movie_id", name="uq_movie_rating_user_movie"
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    movie: Mapped[Movie] = relationship("Movie", back_populates="ratings")
    user: Mapped[User] = relationship("User", back_populates="movie_ratings")

    def __repr__(self):
        return (
            f"MovieRating(user_id={self.user_id}, movie_id={self.movie_id}, "
            f"rating={self.rating})"
        )


class FavoriteMovie(Base):
    __tablename__ = "favorite_movies"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "movie_id", name="uq_favorite_movie_user_movie"
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    movie: Mapped[Movie] = relationship("Movie", back_populates="favorites")
    user: Mapped[User] = relationship("User", back_populates="favorite_movies")

    def __repr__(self):
        return (
            f"FavoriteMovie(user_id={self.user_id}, movie_id={self.movie_id})"
        )


class MovieComment(Base):
    __tablename__ = "movie_comments"
    __table_args__ = (
        Index("ix_movie_comments_movie_id", "movie_id"),
        Index("ix_movie_comments_parent_id", "parent_id"),
        Index("ix_movie_comments_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "movie_comments.id", ondelete="CASCADE"
        ),  # self-referential
        nullable=True,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=func.now(),
        nullable=False,
    )

    # creates:
    # 1. 'parent' attribute on each comment('comment.parent' returns the parent
    # MovieComment or None)
    # 2. replies collection on each comment(automatically created by backref)
    parent = relationship("MovieComment", remote_side=[id], backref="replies")
    movie = relationship("Movie", back_populates="comments")
    user = relationship("User", back_populates="movie_comments")


class VideoStatus(enum.StrEnum):
    """Lifecycle states for an HLS video transcode job."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class VideoFile(Base):
    """Stores metadata for a Movie's HLS video file and transcode status."""

    __tablename__ = "video_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    status: Mapped[VideoStatus] = mapped_column(
        SAEnum(
            VideoStatus,
            name="videostatus",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=VideoStatus.PENDING,
        nullable=False,
    )
    raw_key: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    movie: Mapped[Movie] = relationship("Movie", back_populates="video")

    def __repr__(self) -> str:
        return (
            f"VideoFile(movie_id={self.movie_id}, status={self.status.value})"
        )


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    movies: Mapped[list[Movie]] = relationship(back_populates="certification")

    def __repr__(self):
        return f"Certification(name={self.name})"
