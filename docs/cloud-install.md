# oge.gl Cloud Deployment Guide

This guide documents the default cloud deployment path for `oge.gl` on Fly.io and Supabase.

Use this guide for:

- provisioning the managed PostgreSQL database on Supabase
- deploying the API service to Fly.io
- planning the scraper worker deployment boundary on Fly.io
- running Alembic migrations in a controlled rollout step
- performing repeatable post-deploy verification and operational checks

This repository includes a production API `Dockerfile`, a root `fly.toml`, and a worker process command for queued ingestion execution. The worker discovers eligible filings, downloads and parses PDFs, persists filing and transaction results idempotently, and updates ingestion job state and counts.

Fly.io and Supabase are the default documented deployment targets, not the only supported way to run `oge.gl`. The application can also be deployed natively or on other infrastructure as long as the runtime, database, migration, and service-boundary requirements in the repository documentation are preserved.

For local development and service setup, see [docs/development-requirements.md](./development-requirements.md). For product behavior and API-facing expectations, see [docs/product-specification.md](./product-specification.md) and [docs/software-design.md](./software-design.md).

## 1. Supported Production Architecture

`oge.gl` keeps a strict split between API, scraper workflow, persistence, and frontend responsibilities in production.

Target production serving model:

- Supabase provides the managed PostgreSQL database
- Fly.io runs the API service as the public backend
- Fly.io runs the scraper worker as a separate process boundary
- the API exposes search, filing, and ingestion status endpoints only
- the scraper worker process performs OGE discovery, PDF download, parsing, normalization, and persistence work
- the database remains the system of record for normalized filings, normalized transactions, and ingestion job state
- source PDF provenance remains preserved in stored filing records and transaction provenance fields

Operational notes:

- discovery remains limited to public OGE `278 Transaction` results unless the product specification changes
- public API behavior remains versioned under `/api/v1`
- long-running ingestion work must stay out of synchronous request handlers
- the frontend remains API-driven and must not scrape the OGE source site directly

Repository deployment scope:

- the API service exists and can run locally
- ingestion job endpoints exist and queued-job execution covers the current worker path
- the worker process can claim queued ingestion jobs, persist filing and transaction results, and update job lifecycle events
- a production API `Dockerfile` and root `fly.toml` are committed for the Fly API deployment path
- a Fly worker process command is committed for the persistence-backed ingestion path

## 2. Prerequisites

Create or confirm these operator prerequisites before cloud deployment work:

- a Supabase project with PostgreSQL access
- a Fly.io account and `flyctl`
- repository access to build and deploy the current branch or release
- a production hostname and DNS provider of your choice if you intend to expose a stable public API origin

Local operator tooling:

- Python 3.12+
- `flyctl`
- optional Docker if you add a production image locally before the initial deploy
- optional `psql` for direct database checks

Fly.io CLI notes:

- the `fly` command used in this guide comes from the Fly.io CLI, `flyctl`
- install `flyctl` with the official Fly.io installation instructions for your platform
- verify the CLI is available with `fly version`
- authenticate before creating apps or secrets with `fly auth login`

## 3. Provision Supabase PostgreSQL

1. Create the Supabase project that will hold the `oge.gl` production database.
2. Choose a Supabase region that is close to the intended Fly.io region.
3. In the Supabase project settings, copy the PostgreSQL connection string for application use.
4. Keep SSL enabled in the selected connection string. If you assemble the URL manually, keep `sslmode=require`.
5. Store the database URL in operator secret storage only. Do not commit it to tracked files.
6. Prefer the Supabase direct connection string when the Fly runtime supports the needed network path cleanly. If you need a pooler-compatible fallback, use the Supavisor session-mode URL rather than transaction mode.

Database guidance:

- use the existing Alembic migration chain for schema changes
- keep production tables under Alembic control only
- preserve filing and transaction uniqueness constraints so repeat ingestion remains idempotent
- keep source PDF provenance fields and raw extraction context intact when persistence expands
- use Supabase backups and PITR options according to your retention requirements

## 4. Create the Fly.io Apps

The planned production topology uses at least two Fly.io process boundaries:

- one public API app
- one worker process running from the same image or a separate Fly app, depending on operations preference

Initialize the API app from the repository root:

```bash
cd /path/to/oge.gl
fly auth login
fly launch --no-deploy
```

Recommended Fly launch choices for the API app:

- app name: choose the stable public API app name you intend to keep
- region: choose the closest practical region to the Supabase database
- database: do not provision Fly Postgres for this deployment path
- Redis: not required for the current documented architecture

Current configuration expectations:

- the repository root `Dockerfile` builds the API image
- the repository root `fly.toml` defines both the public `app` process and the background `worker` process and runs migrations from the root `alembic/` setup as a Fly release step
- the backend package lives under the repository root `app/` directory
- the API container should listen on `0.0.0.0:8000`
- the Fly release step should run `alembic upgrade head`
- health checks should target the versioned API health route, `GET /api/v1/health`

Suggested Fly process rollout:

- keep the `app` process attached to the public HTTP service
- run the `worker` process without a public HTTP service
- scale the worker conservatively until the persistence-backed ingestion path is complete

## 5. Configure Runtime Settings on Fly.io

Store runtime settings in Fly secrets or environment configuration, not in tracked files.

Expected API runtime values:

```bash
fly secrets set \
  DATABASE_URL='REPLACE_WITH_SUPABASE_URL' \
  API_HOST='0.0.0.0' \
  API_PORT='8000' \
  OGE_BASE_URL='https://www.oge.gov/web/OGE.nsf/Officials%20Individual%20Disclosures%20Search%20Collection?OpenForm' \
  PDF_STORAGE_DIR='/data/pdfs' \
  INGEST_BATCH_SIZE='100' \
  LOG_LEVEL='INFO' \
  SCRAPER_REQUEST_TIMEOUT='30' \
  SCRAPER_RETRY_LIMIT='3'
```

Runtime guidance:

- `DATABASE_URL` must point to the Supabase PostgreSQL connection string with SSL enabled
- `API_HOST` should remain `0.0.0.0` for Fly runtime binding
- `API_PORT` should remain aligned with the Fly internal port
- `OGE_BASE_URL` should stay pointed at the canonical OGE disclosures collection unless the product specification changes
- `PDF_STORAGE_DIR` is a forward-looking requirement for durable PDF storage and should map to a validated writable location when PDF caching is enabled in production
- `INGEST_BATCH_SIZE`, `SCRAPER_REQUEST_TIMEOUT`, and `SCRAPER_RETRY_LIMIT` should be tuned conservatively until production traffic and ingest volume are understood

Worker guidance:

- the worker uses the same `DATABASE_URL`, `OGE_BASE_URL`, and timeout settings as the API image
- the worker loop uses `INGEST_WORKER_POLL_INTERVAL_SECONDS` and `INGEST_WORKER_MAX_JOBS_PER_RUN`
- worker-specific concurrency should remain conservative until persistence and duplicate-handling are implemented end to end

## 6. Deploy the API Service

Deploy the API service to Fly.io from the repository root using the committed production image and Fly config.

Planned deployment command:

```bash
cd /path/to/oge.gl
fly deploy
```

Release expectations:

- the release step runs `alembic upgrade head` before the new API version serves traffic
- the deployed app reaches a healthy state before DNS cutover or public verification
- the API remains able to connect to Supabase with the configured SSL-enabled `DATABASE_URL`

Initial deployment checks:

- `fly status`
- `fly logs`
- `curl -i https://YOUR_API_HOST/api/v1/health`

## 7. Run Migrations

Production schema changes should run through Alembic in a controlled release step.

Migration expectations:

- `alembic upgrade head` runs before the new application version starts serving traffic
- do not hand-edit the production schema outside Alembic unless you also update repository migration history intentionally
- if the release migration step fails, stop the rollout and resolve the schema issue before retrying
- use a manual Fly console migration command only for investigation or recovery, not as the normal rollout path

Example recovery command if a manual check is required later:

```bash
fly ssh console -C "cd /app && alembic upgrade head"
```

## 8. Deploy the Worker Process

The worker process deploys from the same Fly image using the `worker` process command defined in `fly.toml`.

Worker expectations:

- it claims queued ingestion jobs from the database
- it runs the current discovery, download, parse, and persistence workflow against the OGE collection page
- it updates job state, discovered counts, downloaded counts, ingested counts, warnings, errors, and lifecycle events in PostgreSQL
- it does not serve public HTTP traffic as the main API surface
- it shares the production database with the API service through the same Supabase project
- it keeps long-running ingestion activity out of request-response handling

Suggested Fly operations:

```bash
fly scale count app=1 worker=1
fly machine list
```

## 9. Post-Deploy Verification

Run these checks after the initial deploy and after every production update.

API and database checks:

```bash
curl -i https://YOUR_API_HOST/api/v1/health
curl -i "https://YOUR_API_HOST/api/v1/transactions?page=1&page_size=5"
curl -i https://YOUR_API_HOST/api/v1/ingest/jobs
```

Verification expectations:

- the API health endpoint returns `200`
- the transactions endpoint responds with the documented envelope shape
- the ingestion jobs endpoint responds without leaking internal stack traces or unsafe infrastructure details
- the API can read persisted filing and transaction rows from Supabase

Worker checks:

1. submit a limited ingestion run through `POST /api/v1/ingest/run`
2. verify the job transitions through `queued`, `running`, and a terminal `succeeded` or `failed` state
3. verify `discovered_count`, `downloaded_count`, `ingested_count`, `warning_count`, and `error_count` are updated by the worker
4. verify filings and transactions become queryable through the API without duplicate rows after a repeated run

## 10. Operations and Monitoring

Use Fly.io and Supabase as the primary cloud operations surfaces.

Useful Fly commands:

```bash
fly status
fly logs
fly ssh console
```

Operational checks:

- review Fly logs for startup failures, migration failures, and database connectivity errors
- verify Supabase connectivity after each deploy that changes settings or schema
- verify ingestion job counts, lifecycle events, and failure logs for the worker process
- confirm the configured Fly region and Supabase region are not introducing avoidable latency
- verify the API continues to expose source PDF links intentionally and safely

Observability notes:

- application logs remain the primary troubleshooting surface for request failures, ingestion failures, and startup errors
- health checks come from the API health endpoint and Fly deployment status
- Supabase metrics and logs remain the primary troubleshooting surface for database saturation, connection, and backup concerns

## 11. Common Production Issues

### API fails to connect to Supabase

Check:

- `DATABASE_URL` matches the current Supabase connection string
- the database URL keeps SSL enabled
- the Fly region and Supabase region are not introducing avoidable network issues
- the deployed secret was applied to the intended Fly app

### Migrations fail during rollout

Check:

- the current release image includes the expected Alembic revision files
- the release command is running `alembic upgrade head` against the production Supabase database
- the previous rollout did not leave a partial manual schema change behind

### Health checks fail on Fly

Check:

- the app is binding `0.0.0.0:8000`
- the Fly `internal_port` matches the application bind port
- the health check path is `GET /api/v1/health`
- the app has all required runtime configuration values

### Ingestion jobs remain queued indefinitely

Check:

- the API process can dispatch its in-process queued-job runner after `POST /api/v1/ingest/run`
- the worker process is deployed and running with `python -m app.workers.runner` if the environment relies on a dedicated worker
- the worker can reach Supabase and any configured PDF storage location
- job lifecycle events are being written with actionable failure details

### Source PDF caching is not durable

Check:

- `PDF_STORAGE_DIR` points to a validated writable path
- the selected production storage approach matches the implementation in the active ingestion slice
- the deployment does not assume ephemeral container filesystem storage for long-lived PDF reuse

## 12. Related Documentation

- [README.md](../README.md)
- [docs/product-specification.md](./product-specification.md)
- [docs/development-requirements.md](./development-requirements.md)
- [docs/software-design.md](./software-design.md)
