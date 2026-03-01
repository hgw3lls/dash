"""ensure ingest_runs table exists

Revision ID: 0003_ingest_runs_guard
Revises: 0002_fts5
Create Date: 2026-03-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_ingest_runs_guard"
down_revision = "0002_fts5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "ingest_runs" not in tables:
        op.create_table(
            "ingest_runs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("ran_at", sa.DateTime(), nullable=False),
            sa.Column("source_path", sa.Text(), nullable=False),
            sa.Column("rows_in", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("rows_upserted", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("errors", sa.Integer(), nullable=False, server_default="0"),
        )

    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes("ingest_runs")}
    if "ix_ingest_runs_ran_at" not in indexes:
        op.create_index("ix_ingest_runs_ran_at", "ingest_runs", ["ran_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "ingest_runs" in tables:
        inspector = sa.inspect(bind)
        indexes = {idx["name"] for idx in inspector.get_indexes("ingest_runs")}
        if "ix_ingest_runs_ran_at" in indexes:
            op.drop_index("ix_ingest_runs_ran_at", table_name="ingest_runs")
        op.drop_table("ingest_runs")
