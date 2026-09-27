# LLM Security Evaluation Service

FastAPI service for ingesting and analyzing LLM security evaluation runs.

## Tech Stack

- Python 3.12
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Pydantic v2 / pydantic-settings
- pytest
- Docker / Docker Compose
- Adminer (dev DB UI)

## Project Structure

```
app/
  main.py          # FastAPI application entrypoint
  api/             # HTTP routes
  core/            # Configuration
  db/              # SQLAlchemy engine, session, Base, init
  models/          # ORM models (Run, TestCase, Finding)
  schemas/         # Pydantic schemas (to be added)
  services/        # Business logic (to be added)
tests/
  test_health.py
  test_models.py
Dockerfile
docker-compose.yml
requirements.txt
.env.example
```

## Run

One command starts the API, PostgreSQL, and Adminer:

```bash
docker compose up --build
```

No local Python or Postgres install needed.

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health: `GET /health` → `{"status": "ok"}`
- Adminer: http://localhost:8080

Optional: copy `.env.example` to `.env` to override defaults.

## Stop

```bash
docker compose down
```

To also remove the database volume:

```bash
docker compose down -v
```

## Tests

Run tests inside Docker (no local Python install required):

```bash
docker compose run --rm api pytest
```

## Inspect the database

### Adminer (browser)

Open http://localhost:8080 and sign in with:

| Field | Value |
|---|---|
| System | PostgreSQL |
| Server | `db` |
| Username | value of `POSTGRES_USER` (default `postgres`) |
| Password | value of `POSTGRES_PASSWORD` (default `postgres`) |
| Database | value of `POSTGRES_DB` (default `llm_security`) |

Use the same values from your `.env` / `.env.example`. Do not commit real credentials.

### psql (CLI)

```bash
docker compose exec db psql -U postgres -d llm_security
```

Replace `-U` / `-d` with your configured user and database if you changed them.

Useful checks:

```sql
\dt
\d runs
\d test_cases
\d findings
```

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `postgres` |
| `POSTGRES_DB` | Database name | `llm_security` |
| `POSTGRES_HOST` | Database host (`db` in Compose) | `db` |
| `POSTGRES_PORT` | Database port | `5432` |

Copy `.env.example` to `.env` and adjust values as needed. Do not commit real credentials.

## Data model (current)

```
Run 1 ---- N Finding N ---- 1 TestCase
```

- `Run`: evaluation run + persisted summary counters
- `TestCase`: reusable immutable test definition (stored once)
- `Finding`: result of a TestCase in a specific Run
