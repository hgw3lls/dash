#!/usr/bin/env python3
import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.db.session import SessionLocal
from app.ingest import IngestOptions, ingest_folder


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
