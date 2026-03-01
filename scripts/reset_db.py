#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

from app.core.config import settings


def sqlite_path_from_url(url: str) -> Path | None:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return None
    raw = url[len(prefix) :]
    return (ROOT / raw).resolve() if not raw.startswith("/") else Path(raw)


def main() -> None:
    db_path = sqlite_path_from_url(settings.database_url)
    if db_path and db_path.exists():
        db_path.unlink()
        print(f"Deleted DB: {db_path}")
    else:
        print("No SQLite DB file found to delete.")

    cmd = [sys.executable, "-m", "alembic", "-c", "api/alembic.ini", "upgrade", "head"]
    print("Running migrations:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)
    print("Database reset complete.")


if __name__ == "__main__":
    main()
