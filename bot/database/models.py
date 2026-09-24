"""SQLAlchemy ORM models for users, Notion credentials, and usage counters."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class User(Base):
    """Telegram user profile."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    notion_credential: Mapped[Optional["NotionCredential"]] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    usage_counters: Mapped[list["UsageCounter"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class NotionCredential(Base):
    """Per-user Notion integration token + target database.

    OAuth note (future):
        Telegram bots cannot complete a browser OAuth dance inline easily.
        Store Integration Token today; later swap for OAuth access_token /
        refresh_token columns and a temporary state table for the redirect flow.
    """

    __tablename__ = "notion_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    # Integration token (secret). Prefer encrypting at rest in production.
    integration_token: Mapped[str] = mapped_column(String(512), nullable=False)
    database_id: Mapped[str] = mapped_column(String(64), nullable=False)
    workspace_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="notion_credential")


class UsageCounter(Base):
    """Daily / monthly request counters per user for quota enforcement."""

    __tablename__ = "usage_counters"
    __table_args__ = (
        UniqueConstraint("user_id", "period_type", "period_key", name="uq_usage_period"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # "day" | "month"
    period_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # e.g. "2026-09-24" or "2026-09"
    period_key: Mapped[str] = mapped_column(String(32), nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship(back_populates="usage_counters")
