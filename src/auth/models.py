from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auth.utils import generate_secure_token
from database import Base

if TYPE_CHECKING:
    from users.models import User


class TokenBaseModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        # when create the token, its value is set before flush()
        default=generate_secure_token,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),  # timezone‑aware datetime
        nullable=False,
        default=lambda: datetime.now(UTC) + timedelta(days=1),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


class ActivationToken(TokenBaseModel):
    __tablename__ = "activation_tokens"
    __table_args__ = (UniqueConstraint("user_id"),)

    user: Mapped[User] = relationship(
        "User",
        back_populates="activation_token",
        uselist=False,  # user.activation_token returns an object, not a list
    )

    def __repr__(self):
        return (
            f"ActivationToken(id={self.id}, token={self.token}, "
            f"expires_at={self.expires_at}, user_id={self.user_id})"
        )


class PasswordResetToken(TokenBaseModel):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (UniqueConstraint("user_id"),)

    user: Mapped[User] = relationship(
        "User", back_populates="password_reset_token", uselist=False
    )

    def __repr__(self):
        return (
            f"PasswordResetToken(id={self.id}, token={self.token}, "
            f"expires_at={self.expires_at}, user_id={self.user_id})"
        )


class RefreshToken(TokenBaseModel):
    __tablename__ = "refresh_tokens"

    user: Mapped[User] = relationship(
        "User",
        back_populates="refresh_tokens",
    )

    @classmethod
    def create(
        cls, user_id: int | Mapped[int], days_valid: int, token: str
    ) -> RefreshToken:
        """Factory method to create a new RefreshToken object.

        Simplifies the creation process by automatically calculating and
        setting the expiration date based on the number of days specified.
        """
        expires_at = datetime.now(UTC) + timedelta(days=days_valid)
        return cls(user_id=user_id, token=token, expires_at=expires_at)

    def __repr__(self):
        return (
            f"RefreshToken(id={self.id}, token={self.token}, "
            f"expires_at={self.expires_at}, user_id={self.user_id})"
        )
