from datetime import datetime, date, timedelta, timezone
from typing import List, Optional
import enum

from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy import (
    Enum,
    String,
    Boolean,
    DateTime,
    func,
    ForeignKey,
    Date,
    Text,
    UniqueConstraint
)

from database import Base
from auth.utils import generate_secure_token, hash_password, verify_password
from auth.validators import validate_email, validate_password_complexity


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
    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    activation_token: Mapped["ActivationToken"] = relationship(
        "ActivationToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    password_reset_token: Mapped["PasswordResetToken"] = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"User(id={self.id}, email={self.email}, "
            f"is_active={self.is_active}, group_id={self.group_id})"
        )

    def has_group(self, group_name: UserGroupEnum) -> bool:
        """
        Check if the user has the given group.

        Args:
            group_name: The group to check.

        Returns:
            True if the user has the group, False otherwise.
        """
        return self.group.name == group_name

    @classmethod
    def create(
        cls,
        email: str,
        raw_password: str,
        group_id: int | Mapped[int]
    ) -> "User":
        user = cls(email=email, group_id=group_id)
        user.password = raw_password

        return user

    @property
    def password(self) -> None:
        raise AttributeError(
            "Password is write-only. User the setter to set the password."
        )

    @password.setter
    def password(self, raw_password: str) -> None:
        """
        Validate and set the user's password.

        The given password will be validated, hashed and stored.
        """
        validate_password_complexity(raw_password)
        self._hashed_password = hash_password(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        """
        Verify the given password against the user's hashed password.
        """
        return verify_password(raw_password, self._hashed_password)

    @validates("email")
    def validate_email(self, key: str, email: str) -> str:
        """
        Validates the given email address against email address syntax rules.
        """
        return validate_email(email)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(
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


class TokenBaseModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )
    token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        default=generate_secure_token  # when create the token, its value is set before flush()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # timezone‑aware datetime
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=1)
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )


class ActivationToken(TokenBaseModel):
    __tablename__ = "activation_tokens"

    user: Mapped[User] = relationship(
        "User",
        back_populates="activation_token"
    )

    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self):
        return (
            f"ActivationToken(id={self.id}, token={self.token}, "
            f"expires_at={self.expires_at}, user_id={self.user_id})"
        )


class PasswordResetToken(TokenBaseModel):
    __tablename__ = "password_reset_tokens"

    user: Mapped[User] = relationship(
        "User",
        back_populates="password_reset_token"
    )

    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self):
        return (
            f"PasswordResetToken(id={self.id}, token={self.token}, "
            f"expires_at={self.expires_at}, user_id={self.user_id})"
        )


class RefreshToken(TokenBaseModel):
    __tablename__ = "refresh_tokens"

    user: Mapped["User"] = relationship(
        "User",
        back_populates="refresh_tokens"
    )

    @classmethod
    def create(
        cls,
        user_id: int | Mapped[int],
        days_valid: int,
        token: str
    ) -> "RefreshToken":
        """
        Factory method to create a new RefreshToken object.

        Simplifies the creation process by automatically calculating and 
        setting the expiration date based on the number of days specified.
        """
        expires_at = datetime.now(timezone.utc) + timedelta(days=days_valid)
        return cls(user_id=user_id, token=token, expires_at=expires_at)

    def __repr__(self):
        return (
            f"RefreshToken(id={self.id}, token={self.token}, "
            f"expires_at={self.expires_at}, user_id={self.user_id})"
        )
