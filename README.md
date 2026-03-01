# trackers-dashboard

Local-only monorepo for ingesting tracker CSVs into SQLite and exploring opportunities via FastAPI + React.

## Repo Layout

- `api/` FastAPI backend
- `web/` React + Vite + TypeScript frontend
- `data/` local CSV drop folder (gitignored)
- `db/` local SQLite files (gitignored)
- `logs/` runtime logs folder (gitignored; create locally)
- `scripts/` ingest/dev helper scripts

## Setup (clean checkout)

### 1) Environment

```bash
cp .env.example .env
```

Defaults:

- `DATABASE_URL=sqlite:///../db/app.db`
- `INGEST_FOLDER=../data`
- `API_PORT=8000`
- `WEB_PORT=5173`

### 2) Backend (venv + pip)

```bash
cd api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3) DB init

```bash
cd api
source .venv/bin/activate
alembic upgrade head
```

### 4) Install web deps

```bash
cd web
npm install
```

## Data flow

1. Drop one or more `.csv` files into `data/`.
2. Run ingest via API, CLI, or `make ingest`.
3. Open the dashboard and filter/sort/edit records.

## Run

### Dev runner (API + web concurrently)

```bash
mkdir -p logs
make dev
```

`make dev` writes process logs to:

- `logs/api-dev.log`
- `logs/web-dev.log`

### Individual services

```bash
make api
make web
```

### Ingest and tests

```bash
make ingest
make test
```

Optional web env:

- `VITE_API_URL` (defaults to `http://localhost:8000`)
- `VITE_INGEST_FOLDER` (defaults to `../data`)

## API Endpoints

### Health
- `GET /health` → `{ "status": "ok" }`

### Ingest
- `POST /ingest/folder`
  - body: `{ folder, pattern?, overwrite_user_fields?, type_default? }`
  - returns ingest summary
- `POST /ingest/upload` (multipart form-data)
  - file upload for CSV ingest

### Opportunities
- `GET /opportunities`
  - query: `q`, `type`, `status`, `tag` (repeat), `deadline_from`, `deadline_to`, `due_bucket`, `region_tag`, `sort`, `order`, `page`, `page_size`
  - defaults: `sort=deadline`, `order=asc`, `page_size=50` (max 200)
  - includes computed `deadline_bucket` in response
  - uses SQLite FTS5 `MATCH` search for `q` when available, with automatic fallback to `LIKE`
- `GET /opportunities/{id}`
- `PATCH /opportunities/{id}`
  - updatable: `status`, `notes`, `priority`, `tags` (replace), `region_tag`

### Saved Views
- `GET /views`
- `POST /views`
- `PATCH /views/{id}`
- `DELETE /views/{id}`

### Export
- `GET /export/csv`
- `GET /export/json`

Exports honor the same filtering params as `GET /opportunities`.

## Ingest CLI (cron-friendly)

```bash
python3 scripts/ingest.py --folder data --pattern "*.csv"
```

Options:
- `--overwrite-user-fields` (default false)
- `--type-default <value>`

### Optional watcher

```bash
python3 scripts/watch_ingest.py --folder data --pattern "*.csv" --interval 5
```

### Sample cron line (hourly)

```cron
# 0 * * * * cd /path/to/trackers-dashboard && . api/.venv/bin/activate && python scripts/ingest.py --folder data --pattern "*.csv" >> logs/ingest.log 2>&1
```

## Build production web locally (optional)

```bash
cd web
npm run build
npm run preview
```

## Reset DB

```bash
python3 scripts/reset_db.py
```

This deletes the SQLite DB file (if it exists) and reruns Alembic migrations.

## Troubleshooting

- **CORS error in browser**: ensure API runs on `http://localhost:8000` and web on `http://localhost:5173`, or set `VITE_API_URL` to match.
- **Port conflict**: change `API_PORT`/`WEB_PORT` in `.env`, then restart services.
- **No data in UI**: verify CSV files are in `data/` and run `make ingest`.
- **Missing frontend types/build errors**: run `cd web && npm install` before `npm run build`.

## Make targets

- `make dev` (api + web)
- `make api`
- `make web`
- `make ingest`
- `make test`
- `make reset`
- `make api-install`
- `make web-install`
- `make db-init`
