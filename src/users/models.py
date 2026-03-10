from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from database import Base
from users.enums import GenderEnum, UserGroupEnum
from users.utils import hash_password, verify_password
from users.validators import validate_email, validate_password_complexity

if TYPE_CHECKING:
    from auth.models import ActivationToken, PasswordResetToken, RefreshToken
    from movies.models import (
        FavoriteMovie,
        MovieComment,
        MovieLike,
        MovieRating,
    )


class UserGroup(Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[UserGroupEnum] = mapped_column(
        Enum(UserGroupEnum), nullable=False, unique=True
    )
    users: Mapped[list[User]] = relationship("User", back_populates="group")

    def __repr__(self) -> str:
        return f"UserGroup(id={self.id}, name={self.name})"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    _hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=False
    )
    group: Mapped[UserGroup] = relationship(
        "UserGroup", back_populates="users"
    )
    activation_token: Mapped[ActivationToken | None] = relationship(
        "ActivationToken", back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_token: Mapped[PasswordResetToken | None] = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    profile: Mapped[UserProfile | None] = relationship(
        "UserProfile", back_populates="user", cascade="all, delete-orphan"
    )
    movie_likes: Mapped[list[MovieLike]] = relationship(
        "MovieLike",
        back_populates="user",
        # ORM cascade ensures removing a like from a movie relationship
        # deletes it from DB
        cascade="all, delete-orphan",
    )
    movie_ratings: Mapped[list[MovieRating]] = relationship(
        "MovieRating", back_populates="user", cascade="all, delete-orphan"
    )
    favorite_movies: Mapped[list[FavoriteMovie]] = relationship(
        "FavoriteMovie", back_populates="user", cascade="all, delete-orphan"
    )
    movie_comments: Mapped[list[MovieComment]] = relationship(
        "MovieComment", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"User(id={self.id}, email={self.email}, "
            f"is_active={self.is_active}, group_id={self.group_id})"
        )

    def has_group(self, group_name: UserGroupEnum) -> bool:
        """Check if the user has the given group.

        Args:
            group_name: The group to check.

        Returns:
            True if the user has the group, False otherwise.
        """
        return self.group.name == group_name

    @classmethod
    def create(
        cls, email: str, raw_password: str, group_id: int | Mapped[int]
    ) -> User:
        """Create a new User instance.

        Args:
            email: The email address of the user.
            raw_password: The raw password of the user.
            group_id: The group ID of the user.

        Returns:
            The new User instance.
        """
        user = cls(email=email, group_id=group_id)
        user.password = raw_password

        return user

    @property
    def password(self) -> str:
        """Raise AttributeError when attempting to read the password.

        This is a write-only property. Use the setter to set the password.
        """
        raise AttributeError(
            "Password is write-only. User the setter to set the password."
        )

    @password.setter
    def password(self, raw_password: str) -> None:
        """Validate and set the user's password.

        The given password will be validated, hashed and stored.
        """
        validate_password_complexity(raw_password)
        self._hashed_password = hash_password(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        """Verify the given password against the user's hashed password."""
        return verify_password(raw_password, self._hashed_password)

    @validates("email")
    def validate_email(self, key: str, email: str) -> str:
        """Validates an email address against email address syntax rules."""
        return validate_email(email)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (UniqueConstraint("user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    avatar: Mapped[str | None] = mapped_column(String(255))
    gender: Mapped[GenderEnum | None] = mapped_column(Enum(GenderEnum))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    info: Mapped[str | None] = mapped_column(Text)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    user: Mapped[User] = relationship("User", back_populates="profile")

    def __repr__(self):
        return (
            f"UserProfile(id={self.id}, first_name={self.first_name}, "
            f"last_name={self.last_name}, gender={self.gender}, "
            f"date_of_birth={self.date_of_birth}, user_id={self.user_id})"
        )
