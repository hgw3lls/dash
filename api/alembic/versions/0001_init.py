"""initial schema

Revision ID: 0001_init
Revises:
Create Date: 2026-03-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "opportunities",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("org", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("region_tag", sa.String(length=32), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("posted_date", sa.Date(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("raw", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_opportunities_deadline", "opportunities", ["deadline"])
    op.create_index("ix_opportunities_type", "opportunities", ["type"])
    op.create_index("ix_opportunities_status", "opportunities", ["status"])
    op.create_index("ix_opportunities_priority", "opportunities", ["priority"])
    op.create_index("ix_opportunities_updated_at", "opportunities", ["updated_at"])

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
    )
    op.create_index("ix_tags_name", "tags", ["name"], unique=True)

    op.create_table(
        "opportunity_tags",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("opportunity_id", sa.String(length=64), sa.ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("opportunity_id", "tag_id", name="uq_opportunity_tag_pair"),
    )
    op.create_index("ix_opportunity_tags_opportunity_id", "opportunity_tags", ["opportunity_id"])
    op.create_index("ix_opportunity_tags_tag_id", "opportunity_tags", ["tag_id"])

    op.create_table(
        "saved_views",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("definition_json", sa.Text(), nullable=False),
    )

    op.create_table(
        "ingest_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ran_at", sa.DateTime(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("rows_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_ingest_runs_ran_at", "ingest_runs", ["ran_at"])


def downgrade() -> None:
    op.drop_index("ix_ingest_runs_ran_at", table_name="ingest_runs")
    op.drop_table("ingest_runs")
    op.drop_table("saved_views")
    op.drop_index("ix_opportunity_tags_tag_id", table_name="opportunity_tags")
    op.drop_index("ix_opportunity_tags_opportunity_id", table_name="opportunity_tags")
    op.drop_table("opportunity_tags")
    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_table("tags")
    op.drop_index("ix_opportunities_updated_at", table_name="opportunities")
    op.drop_index("ix_opportunities_priority", table_name="opportunities")
    op.drop_index("ix_opportunities_status", table_name="opportunities")
    op.drop_index("ix_opportunities_type", table_name="opportunities")
    op.drop_index("ix_opportunities_deadline", table_name="opportunities")
    op.drop_table("opportunities")
