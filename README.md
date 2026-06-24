# GeneRX Backend

FastAPI backend scaffold for the GeneRX pharmacogenomics clinical decision support MVP.

## Prerequisites

- Python 3.12
- PostgreSQL (local or AWS RDS)
- DBeaver (optional database client)

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev,etl]"
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. The liveness endpoint is
`GET /api/v1/health`.

## Database and migrations

Set `DATABASE_URL` in `.env`. Use the SQLAlchemy psycopg URL format:

```text
postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
```

Alembic is configured, but this scaffold deliberately contains no schema migration. Database
models and the initial migration require separate approval.

## Architecture

- `app/api`: FastAPI routers and HTTP endpoints
- `app/models`: SQLAlchemy models
- `app/repositories`: database access
- `app/services`: application and clinical workflow logic
- `app/schemas`: API request and response schemas
- `etl`: data parsing and loading, kept separate from API code
- `alembic`: database migrations

