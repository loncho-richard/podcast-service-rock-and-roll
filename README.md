# Rock & Roll Podcast Service

A small REST API for a catalog of rock & roll podcasts. It ingests podcasts from the
iTunes Search API, cleans them, enriches them with their RSS description/language and a
color palette extracted from the cover art, stores them in PostgreSQL, and lets clients
browse, search and export the catalog. Everything, ingestion included, happens through
the API.

Design decisions, trade-offs and the architecture overview are in [NOTES.md](NOTES.md).

## Quick start (Docker)

Prerequisites: Docker with Compose v2.

```bash
git clone <this-repo> && cd podcast-service-rock-and-roll
docker compose up --build
```

Then open **http://localhost:8000/docs**. Migrations run automatically on startup, and
local-only default credentials are baked into `docker-compose.yml`, so no configuration
is needed to try it.

### Try it from the docs page

1. Click **Authorize** and log in with username `reviewer`, password
   `local-dev-secret-change-me` (leave the client fields empty).
2. `POST /ingestion/bulk` → **Try it out** → **Execute**. It takes around 20–30 seconds
   (feeds and covers are downloaded) and returns a summary like:
   ```json
   {"source": "live", "fetched": 136, "stored": 94, "created": 94, "updated": 0,
    "unchanged": 0, "skipped": 42, "palette_failures": 0, "skipped_records": ["..."]}
   ```
   Run it again: nothing is duplicated, everything comes back as `unchanged`.
3. `GET /podcasts` to browse and search, `GET /podcasts/{id}` for one podcast (see its
   `palette`), `GET /podcasts/export` for the whole catalog.

### Or with curl

The first line uses [jq](https://jqlang.org/) to extract the token.

```bash
TOKEN=$(curl -s -X POST localhost:8000/auth/token \
  -d "username=reviewer&password=local-dev-secret-change-me" | jq -r .access_token)
AUTH="Authorization: Bearer $TOKEN"

# Ingest (body optional: custom terms and results per term)
curl -s -X POST localhost:8000/ingestion/bulk -H "$AUTH"
curl -s -X POST localhost:8000/ingestion/bulk -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"terms": ["classic rock"], "limit": 10}'
curl -s -X POST localhost:8000/ingestion/podcasts/1618650164 -H "$AUTH"   # one podcast

# Browse
curl -s "localhost:8000/podcasts?q=punk&language=en&page=1&page_size=10" -H "$AUTH"
curl -s "localhost:8000/podcasts/<id>" -H "$AUTH"

# Export (streamed)
curl -s localhost:8000/podcasts/export -H "$AUTH" -o podcasts.ndjson
curl -s "localhost:8000/podcasts/export?format=csv" -H "$AUTH" -o podcasts.csv
```

### See the offline fallback

If iTunes is down or rate-limits us, ingestion uses a stored sample of real iTunes
responses instead. To see it, point the service at a host that does not exist:

```bash
ITUNES_BASE_URL=https://itunes.invalid docker compose up -d api
```

`POST /ingestion/bulk` then answers with `"source": "fallback"`.

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | public | Service and database health (`503` when the DB is down). |
| POST | `/auth/token` | public | Client credentials (OAuth2 form: `username`/`password`) → bearer JWT. |
| POST | `/ingestion/bulk` | bearer | Search iTunes, clean, enrich, upsert. Idempotent. Returns a summary. |
| POST | `/ingestion/podcasts/{itunes_id}` | bearer | Ingest one podcast. `201` new, `200` existing, `404` unknown, `422` rejected (e.g. not rock), `503` source down. |
| GET | `/podcasts` | bearer | Paginated list (`page`, `page_size` ≤ 100); filters `q` (title/author, case-insensitive), `genre` (exact), `language` (`en` matches `en-US`). |
| GET | `/podcasts/{id}` | bearer | One podcast. |
| GET | `/podcasts/export` | bearer | Whole catalog, streamed as NDJSON (default) or CSV (`?format=csv`). |

Every error uses the same shape:

```json
{"error": {"code": "not_found", "message": "Podcast … was not found.", "details": null}}
```

## Configuration

All settings are environment variables (or a `.env` file). `docker-compose.yml` passes
the ones marked *compose* and gives them local defaults.

| Variable | Default | Notes |
|---|---|---|
| `AUTH_CLIENT_ID` | — (**required**) | Static API client id. *compose*: `reviewer` |
| `AUTH_CLIENT_SECRET` | — (**required**, ≥ 12 chars) | Static API client secret. *compose* |
| `JWT_SECRET` | — (**required**, ≥ 32 chars) | HS256 signing key. *compose* |
| `JWT_TTL_SECONDS` | `3600` | Token lifetime. *compose* |
| `DATABASE_URL` | `postgresql+asyncpg://podcasts:podcasts@localhost:5432/podcasts` | *compose* points it at the `db` service. |
| `LOG_LEVEL` | `INFO` | *compose* |
| `ITUNES_BASE_URL` | `https://itunes.apple.com` | *compose* |
| `ITUNES_COUNTRY` | `US` | iTunes store country. |
| `ITUNES_SEARCH_TERMS` | `["rock and roll", "classic rock", "punk rock", "hard rock", "heavy metal", "rockabilly"]` | JSON list; used when `/ingestion/bulk` gets no `terms`. |
| `HTTP_TIMEOUT_SECONDS` | `10` | Per request to iTunes, feeds and covers. |
| `HTTP_RETRY_ATTEMPTS` | `3` | Attempts against iTunes on transient errors. |
| `HTTP_RETRY_MAX_DELAY_SECONDS` | `8` | Backoff cap (also caps `Retry-After`). |
| `ENRICHMENT_RETRY_ATTEMPTS` | `2` | Attempts for feeds and covers. |
| `ENRICHMENT_CONCURRENCY` | `8` | Podcasts enriched in parallel. |
| `MAX_FEED_BYTES` | `2000000` | RSS download cap (the header is read, the rest truncated). |
| `MAX_COVER_BYTES` | `5000000` | Covers above this are skipped. |
| `DOWNLOAD_DEADLINE_SECONDS` | `30` | Hard cap per feed/cover download, retries included. |
| `PALETTE_SIZE` | `5` | Colors per palette. |

Generate a real secret with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

## Running locally without Docker for the API

Prerequisites: Python 3.12 and [uv](https://docs.astral.sh/uv/). PostgreSQL still comes
from Compose.

```bash
docker compose up -d db
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn podcast_service.api.app:create_app --factory --reload
```

## Tests and checks

```bash
uv sync
uv run pytest                        # everything (needs Docker: starts a throwaway PostgreSQL)
uv run pytest -m "not integration"   # unit tests only, no Docker needed
uv run ruff check . && uv run ruff format --check .
uv run mypy                          # strict
```

Integration tests start their own PostgreSQL container with
[testcontainers](https://testcontainers.com/) and run the real Alembic migrations; they
never touch the Compose database. Nothing in the suite calls the real iTunes, feeds or
images: HTTP is mocked with `respx` and the ingestion ports with in-memory fakes.

`tests/` mirrors `src/`: the tests for `src/podcast_service/x/y.py` live in
`tests/podcast_service/x/test_y.py`, fixtures live only in `conftest.py` files, and
shared builders and fakes are in `tests/factories.py` and `tests/fakes.py`.

## Project layout

```
src/podcast_service/
  domain/          entities, value objects, normalization rules, ports (no framework code)
  application/     use cases: ingestion, queries, auth; unit-of-work port
  infrastructure/  PostgreSQL, iTunes client + offline sample, RSS, images, JWT, retries
  api/             FastAPI routers, schemas, error handling, security, exporters
  container.py     dependency-injection container (composition root)
  config.py        settings
migrations/        Alembic
tests/             mirrors src/
```

Each package exposes its public API in `__init__.py` (`__all__`). Code outside a package
imports from the package (`from podcast_service.domain.podcast import Podcast`); modules
inside it import their siblings directly. `tests/test_architecture.py` enforces this, and
that dependencies only point inwards (`domain` ← `application` ← `infrastructure`).
