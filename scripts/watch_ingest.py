#!/usr/bin/env python3
import argparse
import subprocess
import sys
import time
from pathlib import Path


def snapshot(folder: Path, pattern: str) -> dict[str, float]:
    return {str(path): path.stat().st_mtime for path in sorted(folder.glob(pattern)) if path.is_file()}


def run_ingest(folder: Path, pattern: str, overwrite_user_fields: bool, type_default: str | None) -> int:
    cmd = [sys.executable, "scripts/ingest.py", "--folder", str(folder), "--pattern", pattern]
    if overwrite_user_fields:
        cmd.append("--overwrite-user-fields")
    if type_default:
        cmd.extend(["--type-default", type_default])
    return subprocess.call(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll a folder and trigger CSV ingest on file changes.")
    parser.add_argument("--folder", default="data", help="Folder to watch")
    parser.add_argument("--pattern", default="*.csv", help="Glob pattern to watch")
    parser.add_argument("--interval", type=float, default=5.0, help="Polling interval in seconds")
    parser.add_argument("--overwrite-user-fields", action="store_true")
    parser.add_argument("--type-default", default=None)
    args = parser.parse_args()

    folder = Path(args.folder)
    folder.mkdir(parents=True, exist_ok=True)

    last = snapshot(folder, args.pattern)
    print(f"Watching {folder} ({args.pattern}) every {args.interval}s")

    while True:
        time.sleep(args.interval)
        current = snapshot(folder, args.pattern)
        if current != last:
            print("Change detected. Running ingest...")
            code = run_ingest(folder, args.pattern, args.overwrite_user_fields, args.type_default)
            print(f"Ingest completed with exit code {code}")
            last = current


if __name__ == "__main__":
    main()
