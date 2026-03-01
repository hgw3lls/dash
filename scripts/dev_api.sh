#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../api"

if [[ -x .venv/bin/python ]]; then
  .venv/bin/python -m alembic upgrade head
else
  python -m alembic upgrade head
fi

uvicorn app.main:app --reload --port "${API_PORT:-8000}"
