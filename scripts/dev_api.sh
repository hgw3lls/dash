#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../api"
uvicorn app.main:app --reload --port "${API_PORT:-8000}"
