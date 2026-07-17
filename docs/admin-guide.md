cd

# oge.gl Admin Guide

This guide covers runtime administration for oge.gl, including backend configuration, logging, and deployment workflows.

## Configuration

The backend loads configuration from `config/default.toml` by default.

Override precedence:

1. explicit `Settings(...)` init values
2. environment variables
3. config file values from `APP_CONFIG_FILE` when set, otherwise `config/default.toml`
4. dotenv values
5. file secret values

Environment variables override matching config-file keys.

`DATABASE_URL` values using Fly- or platform-style `postgres://...` or driverless `postgresql://...` PostgreSQL URLs are normalized to `postgresql+psycopg://...` at startup so SQLAlchemy uses the installed `psycopg` driver.

### Configuration Reference

| Setting                                                                           | Default                                                       | Type         | Allowed values                                            |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------- | ------------ | --------------------------------------------------------- |
| `APP_NAME` (`app_name`)                                                       | `oge.gl API`                                                | string       | any non-empty string                                      |
| `APP_VERSION` (`app_version`)                                                 | `0.1.0`                                                     | string       | semantic version string                                   |
| `API_V1_PREFIX` (`api_v1_prefix`)                                             | `/api/v1`                                                   | string       | path prefix string                                        |
| `DATABASE_URL` (`database_url`)                                               | `postgresql+psycopg://postgres:postgres@localhost:5432/oge` | string       | valid SQLAlchemy URL                                      |
| `OGE_BASE_URL` (`oge_base_url`)                                               | OGE disclosures collection URL                                | string       | valid absolute URL                                        |
| `SCRAPER_REQUEST_TIMEOUT` (`scraper_request_timeout`)                         | `30.0`                                                      | float        | positive float                                            |
| `INGEST_WORKER_POLL_INTERVAL_SECONDS` (`ingest_worker_poll_interval_seconds`) | `15.0`                                                      | float        | positive float                                            |
| `INGEST_WORKER_MAX_JOBS_PER_RUN` (`ingest_worker_max_jobs_per_run`)           | `10`                                                        | integer      | positive integer                                          |
| `RUNTIME_ENVIRONMENT` (`runtime_environment`)                                 | `local`                                                     | enum         | `local`, `non_local`                                  |
| `LOG_LEVEL` (`log_level`)                                                     | `INFO`                                                      | string       | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` (`log_format`)                                                   | `auto`                                                      | enum         | `auto`, `json`, `text`                              |
| `LOG_ENABLE_ROW_DEBUG` (`log_enable_row_debug`)                               | `false`                                                     | boolean      | `true`, `false`                                       |
| `LOG_FILE_PATH` (`log_file_path`)                                             | `/var/log/oge.gl/backend.log`                               | string       | writable file path                                        |
| `CORS_ALLOW_ORIGINS` (`cors_allow_origins`)                                   | `http://127.0.0.1:5173`, `http://localhost:5173`          | list[string] | valid origin URLs                                         |
| `APP_CONFIG_FILE`                                                               | `config/default.toml`                                       | string       | readable TOML file path                                   |

Use environment variables for secrets and environment-specific values instead of committing secret values in config files.

### Frontend Manual Fetch Defaults

The frontend manual fetch control uses backend-owned configuration values exposed through the ingestion API.

| Setting                                                           | Default         | Type    | Allowed values              |
| ----------------------------------------------------------------- | --------------- | ------- | --------------------------- |
| `MANUAL_INGEST_DEFAULT_MODE` (`manual_ingest_default_mode`)   | `incremental` | string  | `incremental`             |
| `MANUAL_INGEST_DEFAULT_LIMIT` (`manual_ingest_default_limit`) | `1`           | integer | integer from`1` to `25` |
| `MANUAL_INGEST_MAX_LIMIT` (`manual_ingest_max_limit`)         | `25`          | integer | integer`>= 1`             |

The frontend reads the effective values through `GET /api/v1/ingest/defaults`.
If backend configuration is invalid, startup should fail safely before the frontend receives a malformed defaults payload.
If the defaults API surface is unavailable, the UI should fail safely without submitting a malformed ingestion request.

## Logging

Backend logging behavior:

- API and worker processes use centralized logging configuration.
- `LOG_FORMAT=auto` uses text logs in local runtime and JSON logs in non-local runtime.
- Request identifiers are used as log correlation context after safe header normalization.
- API request failures emit structured log events with request context.
- Ingestion lifecycle logs include job-scoped context where available.
- Row-level parser diagnostics emit only when `LOG_ENABLE_ROW_DEBUG=true` and `LOG_LEVEL=DEBUG`.
- Local runtime writes logs to `LOG_FILE_PATH` and also emits to process output.
- If `LOG_FILE_PATH` is unavailable in local runtime, logs fall back to `/tmp/oge.gl/backend.log` with a warning event.

### Configuration Verification Commands

```bash
cd /path/to/oge.gl
source .venv/bin/activate

# File-backed defaults
python -c "from app.core.config import settings; print(settings.log_level, settings.api_v1_prefix)"

# Environment overrides
LOG_LEVEL=DEBUG API_V1_PREFIX=/api/custom python -c "from app.core.config import Settings; s=Settings(); print(s.log_level, s.api_v1_prefix)"
```

## Deployment

### Local Deployment Quick Start

This quick start deploys oge.gl from a source checkout.

1. Clone the repository.

```bash
git clone https://github.com/t3knoid/oge.gl.git
cd oge.gl
```

2. Deploy PostgreSQL.

```bash
docker run --name oge-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_DB=oge \
  -p 5432:5432 \
  -d postgres:16
```

3. Prepare backend and run migrations.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/oge"
export OGE_BASE_URL="https://www.oge.gov/web/OGE.nsf/Officials%20Individual%20Disclosures%20Search%20Collection?OpenForm"
export LOG_LEVEL="INFO"
export LOG_FORMAT="auto"
export RUNTIME_ENVIRONMENT="local"
export LOG_FILE_PATH="/var/log/oge.gl/backend.log"
export LOG_ENABLE_ROW_DEBUG="false"
export APP_CONFIG_FILE="config/default.toml"
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Seed ingestion and verify.

```bash
source .venv/bin/activate
curl -sS -X POST "http://127.0.0.1:8000/api/v1/ingest/run" \
  -H "Content-Type: application/json" \
  -d '{"mode":"incremental","limit":1}'
curl -sS "http://127.0.0.1:8000/api/v1/ingest/jobs"
```

5. Optional frontend shell.

```bash
cd frontend
npm install
npm run dev
```

Optional backend overrides for manual fetch defaults:

```bash
export MANUAL_INGEST_DEFAULT_MODE="incremental"
export MANUAL_INGEST_DEFAULT_LIMIT="1"
export MANUAL_INGEST_MAX_LIMIT="25"
```

Open `http://127.0.0.1:5173` for UI verification.

### Managed Cloud Deployment (Fly.io + Supabase)

1. Provision Supabase PostgreSQL and capture an SSL-enabled `DATABASE_URL`.
2. Authenticate Fly CLI and initialize app from repository root.

```bash
cd /path/to/oge.gl
fly auth login
fly launch --no-deploy
```

3. Set runtime settings as Fly secrets.

```bash
fly secrets set \
  DATABASE_URL='REPLACE_WITH_SUPABASE_URL' \
  API_HOST='0.0.0.0' \
  API_PORT='8000' \
  OGE_BASE_URL='https://www.oge.gov/web/OGE.nsf/Officials%20Individual%20Disclosures%20Search%20Collection?OpenForm' \
  LOG_LEVEL='INFO' \
  SCRAPER_REQUEST_TIMEOUT='30'
```

If the managed database provider returns a bare `postgres://...` or `postgresql://...` URL, it can be used directly. The backend normalizes that value to the `psycopg` SQLAlchemy driver during startup and release-time migrations.

4. Deploy with release-time migrations.

```bash
cd /path/to/oge.gl
fly deploy
```

5. Scale API and worker processes.

```bash
fly scale count app=1 worker=1
```

6. Verify post-deploy behavior.

```bash
curl -i https://YOUR_API_HOST/api/v1/health
curl -i "https://YOUR_API_HOST/api/v1/transactions?page=1&page_size=5"
curl -i https://YOUR_API_HOST/api/v1/ingest/jobs
```

For architecture and local development requirements, see [docs/development-requirements.md](development-requirements.md).
For product behavior and API expectations, see [docs/product-specification.md](product-specification.md).
