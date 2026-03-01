.PHONY: dev api web ingest test api-install db-init reset web-install

api-install:
	cd api && python3.12 -m venv .venv && . .venv/bin/activate && pip install -e .[dev]

web-install:
	cd web && npm install

db-init:
	cd api && . .venv/bin/activate && alembic upgrade head

api:
	./scripts/dev_api.sh

web:
	./scripts/dev_web.sh

dev:
	@bash -lc 'set -euo pipefail; mkdir -p logs; \
	./scripts/dev_api.sh > logs/api-dev.log 2>&1 & api_pid=$$!; \
	./scripts/dev_web.sh > logs/web-dev.log 2>&1 & web_pid=$$!; \
	trap "kill $$api_pid $$web_pid" INT TERM EXIT; \
	wait'

ingest:
	python3 scripts/ingest.py --folder data --pattern "*.csv"

test:
	cd api && . .venv/bin/activate && pytest

reset:
	python3 scripts/reset_db.py
