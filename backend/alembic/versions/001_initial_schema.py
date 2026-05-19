"""Initial schema — all 8 tables

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2025-05-10 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e5f6"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── organizations ──────────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clerk_org_id", sa.String(255), unique=True, nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("plan", sa.String(20), nullable=False, server_default="free"),
        sa.Column(
            "settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "plan IN ('free', 'pro', 'enterprise')", name="ck_org_plan"
        ),
    )
    op.create_index("ix_organizations_clerk_org_id", "organizations", ["clerk_org_id"])
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clerk_id", sa.String(255), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_users_clerk_id", "users", ["clerk_id"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── organization_members ───────────────────────────────────────────────────
    op.create_table(
        "organization_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False, server_default="analyst"),
        sa.Column(
            "invited_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # TimestampMixin columns
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
        sa.CheckConstraint("role IN ('admin', 'analyst')", name="ck_member_role"),
    )
    op.create_index("ix_org_members_org_id", "organization_members", ["organization_id"])
    op.create_index("ix_org_members_user_id", "organization_members", ["user_id"])

    # ── research_reports ───────────────────────────────────────────────────────
    op.create_table(
        "research_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column(
            "companies",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="ARRAY[]::varchar[]",
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="created"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "report_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "generation_context",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="ARRAY[]::varchar[]",
        ),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_pinned", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("processing_time_ms", sa.Integer, nullable=True),
        sa.Column("total_tokens_used", sa.Integer, nullable=True),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column(
            "tools_called",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="ARRAY[]::varchar[]",
        ),
        sa.Column("cache_hit", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('created','planning','dispatching','synthesizing',"
            "'completed','partial','failed','cancelled')",
            name="ck_report_status",
        ),
    )
    op.create_index("ix_reports_org_created", "research_reports", ["organization_id", "created_at"])
    op.create_index("ix_reports_org_status", "research_reports", ["organization_id", "status"])
    op.create_index(
        "ix_reports_companies", "research_reports", ["companies"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_reports_tags", "research_reports", ["tags"],
        postgresql_using="gin",
    )

    # ── report_sources ─────────────────────────────────────────────────────────
    op.create_table(
        "report_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("research_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.CheckConstraint(
            "source_type IN ('market_api','news_api','vector_db','filing')",
            name="ck_source_type",
        ),
    )
    op.create_index("ix_sources_report_id", "report_sources", ["report_id"])

    # ── watchlist_items ────────────────────────────────────────────────────────
    op.create_table(
        "watchlist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "organization_id", "user_id", "ticker",
            name="uq_watchlist_org_user_ticker",
        ),
    )
    op.create_index("ix_watchlist_org_user", "watchlist_items", ["organization_id", "user_id"])

    # ── query_cache ────────────────────────────────────────────────────────────
    op.create_table(
        "query_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cache_key", sa.String(512), unique=True, nullable=False),
        sa.Column(
            "report_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("hit_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cache_key", "query_cache", ["cache_key"], unique=True)
    op.create_index("ix_cache_expires_at", "query_cache", ["expires_at"])

    # ── audit_logs ─────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "before_state",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "after_state",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("ip_address", postgresql.INET, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_audit_org_created", "audit_logs", ["organization_id", "created_at"])
    op.create_index("ix_audit_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_user_id", "audit_logs", ["user_id"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("audit_logs")
    op.drop_table("query_cache")
    op.drop_table("watchlist_items")
    op.drop_table("report_sources")
    op.drop_table("research_reports")
    op.drop_table("organization_members")
    op.drop_table("users")
    op.drop_table("organizations")