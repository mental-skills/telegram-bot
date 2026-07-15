from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class SessionStatus(StrEnum):
    active = "active"
    completed = "completed"
    reset = "reset"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    age_group: Mapped[str | None] = mapped_column(String(8), nullable=True)
    locale: Mapped[str] = mapped_column(String(8), default="ru")
    privacy_version: Mapped[str] = mapped_column(String(32), default="2026-07-15")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sessions: Mapped[list[TrainerSession]] = relationship(back_populates="user")


class TrainerSession(Base):
    __tablename__ = "trainer_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    module_id: Mapped[str] = mapped_column(String(64), default="football_parent_mvp")
    scenario_id: Mapped[str] = mapped_column(String(64), index=True)
    content_version: Mapped[str] = mapped_column(String(64))
    current_node: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(24), default=SessionStatus.active.value, index=True)
    current_revision: Mapped[int] = mapped_column(Integer, default=1)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_no: Mapped[int] = mapped_column(Integer, default=1)

    user: Mapped[User] = relationship(back_populates="sessions")
    choices: Mapped[list[ChoiceEvent]] = relationship(back_populates="session")


class ChoiceEvent(Base):
    __tablename__ = "choice_events"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "from_node", "option_id", name="uq_choice_once_per_node_option"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("trainer_sessions.id", ondelete="CASCADE"))
    scenario_id: Mapped[str] = mapped_column(String(64), index=True)
    from_node: Mapped[str] = mapped_column(String(128))
    option_id: Mapped[str] = mapped_column(String(32))
    to_node: Mapped[str] = mapped_column(String(128))
    tracking_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    assessment_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[TrainerSession] = relationship(back_populates="choices")


class ContentVersion(Base):
    __tablename__ = "content_versions"
    __table_args__ = (UniqueConstraint("scenario_id", "version", name="uq_content_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[str] = mapped_column(String(64))
    checksum: Mapped[str] = mapped_column(String(64))
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class TechnicalEvent(Base):
    __tablename__ = "technical_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("trainer_sessions.id", ondelete="SET NULL"), nullable=True
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
