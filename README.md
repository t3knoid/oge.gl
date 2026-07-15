# oge.gl

`oge.gl` is a searchable web application for U.S. Office of Government Ethics transaction disclosures.

The detailed product and development documentation lives under [docs/](docs/).

The repository keeps backend Python components in [app/](app), Alembic migrations in [alembic/](alembic), pytest suites in [tests/](tests), and frontend assets in [frontend/](frontend).

## Documentation

- [User guide](docs/user-guide.md)
- [Product specification](docs/product-specification.md)
- [Development requirements](docs/development-requirements.md)
- [Local ingestion workflow](docs/development-requirements.md#local-development-workflow)
- [Frontend local run workflow](frontend/README.md#local-run)
- [Software design](docs/software-design.md)
- [Cloud deployment guide](docs/cloud-install.md)

## Quick Start Deployment

This quick start deploys oge.gl from a source checkout. Backend and frontend processes run directly from this repository (no prebuilt oge.gl application image).

0. Clone the source repository.

```bash
git clone https://github.com/t3knoid/oge.gl.git
cd oge.gl
```

1. Deploy the database.

```bash
docker run --name oge-postgres \
	-e POSTGRES_PASSWORD=postgres \
	-e POSTGRES_USER=postgres \
	-e POSTGRES_DB=oge \
	-p 5432:5432 \
	-d postgres:16
```

2. Prepare the backend and run migrations.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/oge"
export OGE_BASE_URL="https://www.oge.gov/web/OGE.nsf/Officials%20Individual%20Disclosures%20Search%20Collection?OpenForm"
alembic upgrade head
```

3. Seed the database through ingestion.

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

With the backend running, open the API docs at:

- http://127.0.0.1:8000/docs (Swagger UI)
- http://127.0.0.1:8000/openapi.json (OpenAPI schema)

In a second terminal:

```bash

source .venv/bin/activate
curl -sS -X POST "http://127.0.0.1:8000/api/v1/ingest/run" \
	-H "Content-Type: application/json" \
	-d '{"mode":"incremental","limit":1}'
curl -sS "http://127.0.0.1:8000/api/v1/ingest/jobs"
```

4. Run the frontend.

In a third terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173 and verify that results are returned from the seeded backend API.

## Summary

The application is intended to:

1. Discover public OGE Form 278-T filings.
2. Download and scrape transaction PDFs.
3. Normalize and store filing and transaction data.
4. Expose the data through an API.
5. Provide a searchable frontend for filer, asset, trade type, date, and amount.
