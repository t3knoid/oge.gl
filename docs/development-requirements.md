# oge.gl Development Requirements

## Goal

This document defines the recommended application stack, service boundaries, local development expectations, and non-functional requirements for implementing `oge.gl`.

## Recommended Stack

### Scraper Service

- Python 3.12+
- `pdfplumber` for PDF text extraction
- `rapidfuzz` for fuzzy row cleanup and parser heuristics
- `httpx` or `requests` for HTTP fetching
- `beautifulsoup4` or `lxml` for parsing discovery pages

### API Service

- Python 3.12+
- FastAPI
- SQLAlchemy or SQLModel
- Pydantic
- Uvicorn

### Database

- PostgreSQL 16+

### Frontend

- React
- TypeScript
- Vite or Next.js
- a simple data table implementation with server-driven filtering and pagination

## Service Boundaries

### Scraper

Responsibilities:

- query the OGE search site
- discover `278 Transaction` results
- download and cache PDFs
- parse and normalize filing data
- persist results or publish them for API-side persistence

### API

Responsibilities:

- expose transaction and filing records
- support filtering and pagination
- provide ingestion status endpoints
- enforce schema validation and response shaping

### Web App

Responsibilities:

- render search controls and results
- preserve filter state in the URL
- link results to original PDFs
- consume only API endpoints, not the OGE source site directly

## Suggested Repository Structure

```text
oge.gl/
  app/
  alembic/
  tests/
  frontend/
  fixtures/
  docs/
```

Suggested additions within each project:

- `app/api/`
- `app/core/`
- `app/services/`
- `tests/api/`
- `tests/scraper/`
- `frontend/src/`
- `frontend/tests/`
- `fixtures/pdfs/`

## Environment Requirements

### Local Tooling

- Python package manager: `uv` or `pip`
- Node.js 22+
- npm, pnpm, or yarn
- PostgreSQL instance for local development

### Environment Variables

The implementation should support environment variables similar to:

- `DATABASE_URL`
- `OGE_BASE_URL`
- `PDF_STORAGE_DIR`
- `INGEST_BATCH_SIZE`
- `LOG_LEVEL`

Possible API-specific variables:

- `API_HOST`
- `API_PORT`
- `CORS_ALLOWED_ORIGINS`

Possible scraper-specific variables:

- `SCRAPER_USER_AGENT`
- `SCRAPER_REQUEST_TIMEOUT`
- `SCRAPER_RETRY_LIMIT`

## Database Requirements

The database layer should support:

- normalized filing and transaction tables
- unique constraints for duplicate prevention
- indexes for text and range filtering
- storage of raw extraction data for auditability

Recommended constraints:

- unique constraint on filing external identity or canonical PDF URL
- unique constraint on transaction row identity within a filing when feasible

## API Requirements

The API should provide:

- `GET /health`
- `GET /transactions`
- `GET /transactions/:id`
- `GET /filings`
- optional internal ingestion endpoints such as `POST /ingest/run`

Behavior requirements:

- pagination is required
- sorting is required
- filter composition is required
- response schemas should be explicit and versionable

## Scraper Requirements

The scraper implementation should:

1. discover OGE filings through the public search page
2. filter for `278 Transaction`
3. resolve the PDF link from the `Type` column
4. download and checksum each PDF
5. extract transaction rows with `pdfplumber`
6. normalize amount, date, and trade type fields
7. preserve raw extracted text for debugging and audit

The scraper should be built so parser logic can be improved without redownloading all source data.

## Frontend Requirements

The frontend should implement:

- search inputs for filer name, description, trade type, date, and amount
- result rendering with pagination
- loading, empty, and error states
- direct links to source PDFs

The frontend should not contain any scraping logic.

## Testing Requirements

Minimum expected test coverage:

- Python backend and scraper unit tests should use `pytest`.
- parser tests against sample PDFs
- normalization tests for amount and date handling
- API tests for each required filter
- integration test for end-to-end ingestion of a sample filing
- frontend tests for filter serialization and result rendering

## Logging and Observability

The services should log:

- discovered filings count
- download failures
- parse failures
- normalization warnings
- ingestion upsert counts
- API request failures

Useful additions if implemented:

- ingestion job history
- row-level extraction diagnostics
- admin-only ingestion status endpoints

## Local Development Workflow

Supported local ingestion workflow:

1. start PostgreSQL
2. prepare a Python environment and install dependencies
3. export required environment values
4. run database migrations
5. start the API service
6. submit an ingestion job through the API
7. verify ingestion job status and persisted results through API endpoints
8. optionally run the dedicated worker loop for continuous queue draining

### Local Setup Commands

Use one terminal for setup and API startup.

```bash
cd /path/to/oge.gl
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/oge"
export OGE_BASE_URL="https://www.oge.gov/web/OGE.nsf/Officials%20Individual%20Disclosures%20Search%20Collection?OpenForm"
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Ingestion Submission And Verification Commands

Use another terminal while the API is running.

```bash
cd /path/to/oge.gl
source .venv/bin/activate

curl -sS -X POST "http://127.0.0.1:8000/api/v1/ingest/run" \
  -H "Content-Type: application/json" \
  -d '{"mode":"incremental","limit":1}'

curl -sS "http://127.0.0.1:8000/api/v1/ingest/jobs"
curl -sS "http://127.0.0.1:8000/api/v1/transactions?page=1&page_size=5"
curl -sS "http://127.0.0.1:8000/api/v1/transactions/REPLACE_WITH_TRANSACTION_ID"
curl -sS "http://127.0.0.1:8000/api/v1/filings/REPLACE_WITH_FILING_ID"
```

Use a transaction ID from the list response, then use the filing ID from the transaction detail response to verify filing data and source PDF provenance.

Repeat the same `POST /api/v1/ingest/run` call to confirm idempotent behavior and verify filing and transaction endpoints remain duplicate-safe for repeated ingestion.

### Optional Dedicated Worker Commands

`POST /api/v1/ingest/run` dispatches an in-process queue runner after creating the job, so a dedicated worker process is optional for local runs.

Use a third terminal only when you want a continuously polling worker loop.

```bash
cd /path/to/oge.gl
source .venv/bin/activate
python -m app.workers.runner
```

### Frontend Local Shell Workflow

Use a separate terminal for the frontend shell.

```bash
cd /path/to/oge.gl/frontend
npm install
npm run dev
```

Optional API base URL override:

```bash
cd /path/to/oge.gl/frontend
VITE_API_BASE_URL="http://127.0.0.1:8000/api/v1" npm run dev
```

The frontend shell runs on Vite's default local address (`http://127.0.0.1:5173`) and provides baseline search and transaction-detail route placeholders for API-driven development.

Use the frontend workspace scripts for local verification when frontend dependencies or routes change:

```bash
cd /path/to/oge.gl/frontend
npm run lint
npm run test
npm run build
npm run audit
```

### Local Limitations And Troubleshooting

- The frontend shell provides route and state placeholders only; full search controls and result rendering land in follow-up implementation slices.
- API and worker diagnostics are available in process logs from `uvicorn` and `python -m app.workers.runner`.
- Run focused backend verification with `pytest -q tests/api/test_ingestion_worker.py tests/api/test_filing_and_ingestion_routes.py` when changing ingestion orchestration behavior.

The shared backend package keeps API, worker, and scraper execution programmatic while the ingestion workflow persists filing records, reconciles transaction rows, and updates ingestion job counters.

## Deployment Considerations

Initial deployment should prioritize:

- repeatable ingestion
- low operational complexity
- clear separation between public web traffic and ingestion jobs

A simple early deployment model is:

- one API service
- one frontend application
- one queued ingestion execution path that the API can trigger in-process with serialized background dispatch
- one optional scheduled or continuously polling worker service for dedicated queued ingestion execution
- one PostgreSQL database

For the default managed cloud path on Fly.io and Supabase, see [docs/cloud-install.md](./cloud-install.md).

That cloud path is the default documented deployment target, not a requirement that excludes native deployment. `oge.gl` can also run on a native host or another platform if the documented stack, migration flow, database requirements, and service boundaries are kept intact.

The repository root includes these production API deployment artifacts:

- `Dockerfile` for the public API image
- `fly.toml` for Fly.io API deployment and release-time migrations
- a worker process command for dedicated queued ingestion execution when a separate worker process is preferred

## Documentation Expectations

As implementation begins, add further documents under `docs/` for:

- software design details including exact API schemas, schema constraints, migration strategy, ingestion workflow, deployment topology, and monitoring thresholds
- cloud deployment steps for the supported managed hosting path
- parser edge cases
- API examples
- ingestion operations

## Summary

The development baseline for `oge.gl` should be a Python-based scraper and API, a PostgreSQL database, and a React-based frontend. The implementation should emphasize reproducible ingestion, normalized searchable data, and traceability back to the original OGE PDFs.
