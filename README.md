# LLM Security Evaluation Service

Initial project infrastructure for an LLM security evaluation API.

## Tech Stack

- Python 3.12
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Pydantic v2 / pydantic-settings
- pytest
- Docker / Docker Compose

## Project Structure

```
app/
  main.py          # FastAPI application entrypoint
  api/             # HTTP routes
  core/            # Configuration
  db/              # SQLAlchemy engine, session, Base
  models/          # ORM models (to be added)
  schemas/         # Pydantic schemas (to be added)
  services/        # Business logic (to be added)
tests/
  test_health.py
Dockerfile
docker-compose.yml
requirements.txt
.env.example
```

## Run

```bash
cp .env.example .env
docker compose up --build
```

API: http://localhost:8000  
Swagger: http://localhost:8000/docs  
Health: `GET /health` → `{"status": "ok"}`

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

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `postgres` |
| `POSTGRES_DB` | Database name | `llm_security` |
| `POSTGRES_HOST` | Database host (`db` in Compose) | `db` |
| `POSTGRES_PORT` | Database port | `5432` |

Copy `.env.example` to `.env` and adjust values as needed. Do not commit real credentials.
