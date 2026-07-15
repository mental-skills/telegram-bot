"""Initial MVP schema.

Revision ID: 20260715_0001
Revises:
Create Date: 2026-07-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260715_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("age_group", sa.String(length=8), nullable=True),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("privacy_version", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_user_id"),
    )
    op.create_index(op.f("ix_users_telegram_user_id"), "users", ["telegram_user_id"])

    op.create_table(
        "content_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scenario_id", "version", name="uq_content_version"),
    )
    op.create_index(op.f("ix_content_versions_scenario_id"), "content_versions", ["scenario_id"])

    op.create_table(
        "trainer_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("module_id", sa.String(length=64), nullable=False),
        sa.Column("scenario_id", sa.String(length=64), nullable=False),
        sa.Column("content_version", sa.String(length=64), nullable=False),
        sa.Column("current_node", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("current_revision", sa.Integer(), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trainer_sessions_scenario_id"), "trainer_sessions", ["scenario_id"])
    op.create_index(op.f("ix_trainer_sessions_status"), "trainer_sessions", ["status"])
    op.create_index(op.f("ix_trainer_sessions_user_id"), "trainer_sessions", ["user_id"])

    op.create_table(
        "choice_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.String(length=64), nullable=False),
        sa.Column("from_node", sa.String(length=128), nullable=False),
        sa.Column("option_id", sa.String(length=32), nullable=False),
        sa.Column("to_node", sa.String(length=128), nullable=False),
        sa.Column("tracking_code", sa.String(length=64), nullable=True),
        sa.Column("assessment_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["session_id"], ["trainer_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id", "from_node", "option_id", name="uq_choice_once_per_node_option"
        ),
    )
    op.create_index(op.f("ix_choice_events_scenario_id"), "choice_events", ["scenario_id"])

    op.create_table(
        "technical_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["session_id"], ["trainer_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_technical_events_event_type"), "technical_events", ["event_type"])


def downgrade() -> None:
    op.drop_index(op.f("ix_technical_events_event_type"), table_name="technical_events")
    op.drop_table("technical_events")
    op.drop_index(op.f("ix_choice_events_scenario_id"), table_name="choice_events")
    op.drop_table("choice_events")
    op.drop_index(op.f("ix_trainer_sessions_user_id"), table_name="trainer_sessions")
    op.drop_index(op.f("ix_trainer_sessions_status"), table_name="trainer_sessions")
    op.drop_index(op.f("ix_trainer_sessions_scenario_id"), table_name="trainer_sessions")
    op.drop_table("trainer_sessions")
    op.drop_index(op.f("ix_content_versions_scenario_id"), table_name="content_versions")
    op.drop_table("content_versions")
    op.drop_index(op.f("ix_users_telegram_user_id"), table_name="users")
    op.drop_table("users")
