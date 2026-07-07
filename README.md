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

Set `DATABASE_URL` in the root `.env`, or fill in the individual database
fields. For AWS RDS, `sslmode=require` is the expected default.

```text
postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
```

Alembic is configured, but this scaffold deliberately contains no schema migration. Database
models and the initial migration require separate approval.

## ETL

Data is fetched live from the [CPIC API](https://github.com/cpicpgx/cpic-data/wiki)
(`https://api.cpicpgx.org/v1`) for the gene-drug pairs defined in `etl/runner.py`
(CYP2C19/clopidogrel, CYP2C19/sertraline, CYP2D6/metoprolol, CYP2C9/warfarin,
VKORC1/warfarin). No local data files are required. After installing the ETL
extras, run:

```powershell
python -m etl.runner
```

## Architecture

- `app/api`: shared FastAPI routers and HTTP endpoints
- `app/authentication`: feature module with routes, service, repo, schemas, and models
- `app/db`: SQLAlchemy base and async session handling
- `app/core`: configuration and logging
- `etl`: fetches CPIC gene/drug/allele/recommendation data from the CPIC API and loads it into
  the database, kept separate from API code
- `alembic`: database migrations
