#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../web"
npm run dev -- --port "${WEB_PORT:-5173}"
