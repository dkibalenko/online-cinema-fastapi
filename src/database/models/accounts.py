from typing import List, Optional
import enum
from datetime import datetime, date, timedelta, timezone

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    Enum,
    Integer,
    String,
    Boolean,
    DateTime,
    func,
    ForeignKey,
    Date,
    Text,
    UniqueConstraint
)

from database.models.base import Base


class UserGroupEnum(str, enum.Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class GenderEnum(str, enum.Enum):
    MAN = "man"
    WOMAN = "woman"


class UserGroup(Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    name: Mapped[UserGroupEnum] = mapped_column(
        Enum(UserGroupEnum),
        nullable=False,
        unique=True
    )
    users: Mapped[List["User"]] = relationship("User", back_populates="group")

    def __repr__(self) -> str:
        return f"UserGroup(id={self.id}, name={self.name})"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True
    )
    _hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("user_groups.id", ondelete="CASCADE"),
        nullable=False
    )
    group: Mapped["UserGroup"] = relationship(
        "UserGroup",
        back_populates="users"
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    avatar: Mapped[Optional[str]] = mapped_column(String(255))
    gender: Mapped[Optional[GenderEnum]] = mapped_column(Enum(GenderEnum))
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    info: Mapped[Optional[str]] = mapped_column(Text)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    user: Mapped[User] = relationship("User", back_populates="profile")

    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self):
        return (
            f"UserProfile(id={self.id}, first_name={self.first_name}, "
            f"last_name={self.last_name}, gender={self.gender}, "
            f"date_of_birth={self.date_of_birth}, user_id={self.user_id})"
        )