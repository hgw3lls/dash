#!/usr/bin/env python3
import argparse
import logging
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from sqlalchemy import inspect

from app.db.session import SessionLocal, engine
from app.ingest import IngestOptions, ingest_folder


logger = logging.getLogger(__name__)


def _python_for_alembic() -> str:
    venv_python = ROOT / "api" / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _verify_required_tables() -> None:
    required_tables = {"opportunities", "tags", "opportunity_tags", "saved_views", "ingest_runs"}
    available_tables = set(inspect(engine).get_table_names())
    missing_tables = sorted(required_tables - available_tables)
    if missing_tables:
        missing = ", ".join(missing_tables)
        logger.error(
            "Database schema is still incomplete after migration. Missing: %s. "
            "Run `cd api && alembic upgrade head` (or reset with `rm -f db/app.db && cd api && alembic upgrade head`) and retry.",
            missing,
        )
        raise SystemExit(1)


def ensure_schema_up_to_date() -> None:
    try:
        subprocess.run(
            [_python_for_alembic(), "-m", "alembic", "upgrade", "head"],
            cwd=ROOT / "api",
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.error(
            "Failed to migrate database schema before ingest. "
            "Run `make migrate` (or `cd api && alembic upgrade head`) and retry."
        )
        raise SystemExit(exc.returncode) from exc

    _verify_required_tables()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest CSV files into trackers-dashboard SQLite DB")
    parser.add_argument("--folder", default="../data", help="Folder containing CSV files")
    parser.add_argument("--pattern", default="*.csv", help="Glob pattern, e.g. '*.csv'")
    parser.add_argument(
        "--overwrite-user-fields",
        action="store_true",
        help="Allow ingest to overwrite status/notes user fields",
    )
    parser.add_argument("--type-default", default=None, help="Default type when not derivable")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    ensure_schema_up_to_date()

    options = IngestOptions(
        folder=args.folder,
        pattern=args.pattern,
        overwrite_user_fields=args.overwrite_user_fields,
        type_default=args.type_default,
    )

    with SessionLocal() as db:
        summary = ingest_folder(db, options)

    print("Ingest summary")
    print(f"- folder: {options.folder}")
    print(f"- pattern: {options.pattern}")
    print(f"- files processed: {summary.files_processed}")
    print(f"- rows read: {summary.rows_read}")
    print(f"- rows upserted: {summary.rows_upserted}")
    print(f"- errors: {summary.errors}")


if __name__ == "__main__":
    main()
