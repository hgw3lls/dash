"""add opportunities fts5 table and sync triggers

Revision ID: 0002_fts5
Revises: 0001_init
Create Date: 2026-03-01
"""

from alembic import op

revision = "0002_fts5"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS opportunities_fts
        USING fts5(id UNINDEXED, title, org, location, description);
        """
    )

    op.execute(
        """
        INSERT INTO opportunities_fts (id, title, org, location, description)
        SELECT id, COALESCE(title,''), COALESCE(org,''), COALESCE(location,''), COALESCE(description,'')
        FROM opportunities;
        """
    )

    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS opportunities_ai AFTER INSERT ON opportunities BEGIN
          INSERT INTO opportunities_fts(id, title, org, location, description)
          VALUES (new.id, COALESCE(new.title,''), COALESCE(new.org,''), COALESCE(new.location,''), COALESCE(new.description,''));
        END;
        """
    )

    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS opportunities_ad AFTER DELETE ON opportunities BEGIN
          DELETE FROM opportunities_fts WHERE id = old.id;
        END;
        """
    )

    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS opportunities_au AFTER UPDATE ON opportunities BEGIN
          DELETE FROM opportunities_fts WHERE id = old.id;
          INSERT INTO opportunities_fts(id, title, org, location, description)
          VALUES (new.id, COALESCE(new.title,''), COALESCE(new.org,''), COALESCE(new.location,''), COALESCE(new.description,''));
        END;
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS opportunities_au;")
    op.execute("DROP TRIGGER IF EXISTS opportunities_ad;")
    op.execute("DROP TRIGGER IF EXISTS opportunities_ai;")
    op.execute("DROP TABLE IF EXISTS opportunities_fts;")
