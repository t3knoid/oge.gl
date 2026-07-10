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

Recommended workflow:

1. start PostgreSQL
2. run database migrations
3. run scraper against a small fixture or a limited live batch
4. start the API service
5. start the frontend app
6. validate search and source PDF links in the browser

### API Startup Commands

Example local API startup flow:

```bash
cd /path/to/oge.gl
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/oge"
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Scraper Startup Commands

Example local scraper setup flow:

```bash
cd /path/to/oge.gl
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

The shared backend package keeps API, worker, and scraper execution programmatic while the ingestion workflow remains partially implemented.

## Deployment Considerations

Initial deployment should prioritize:

- repeatable ingestion
- low operational complexity
- clear separation between public web traffic and ingestion jobs

A simple early deployment model is:

- one API service
- one frontend application
- one scheduled or continuously polling worker service for queued ingestion execution
- one PostgreSQL database

For the default managed cloud path on Fly.io and Supabase, see [docs/cloud-install.md](./cloud-install.md).

That cloud path is the default documented deployment target, not a requirement that excludes native deployment. `oge.gl` can also run on a native host or another platform if the documented stack, migration flow, database requirements, and service boundaries are kept intact.

The repository root includes these production API deployment artifacts:

- `Dockerfile` for the public API image
- `fly.toml` for Fly.io API deployment and release-time migrations
- a worker process command for queued ingestion execution

## Documentation Expectations

As implementation begins, add further documents under `docs/` for:

- software design details including exact API schemas, schema constraints, migration strategy, ingestion workflow, deployment topology, and monitoring thresholds
- cloud deployment steps for the supported managed hosting path
- parser edge cases
- API examples
- ingestion operations

## Summary

The development baseline for `oge.gl` should be a Python-based scraper and API, a PostgreSQL database, and a React-based frontend. The implementation should emphasize reproducible ingestion, normalized searchable data, and traceability back to the original OGE PDFs.
