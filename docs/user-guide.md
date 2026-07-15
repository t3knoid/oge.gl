# oge.gl User Guide

## Purpose

`oge.gl` helps users search U.S. Office of Government Ethics transaction disclosures and verify each result against its source filing PDF.

The current local usage path is API-first. The local frontend shell can display and verify results after the API has seeded data.

## Data Source And Provenance

`oge.gl` ingestion targets OGE Form 278-T disclosures where the source `Type` is `278 Transaction`.

Search results keep source metadata and source PDF links so users can verify returned records against original filings.

## Required Search Fields

Use these fields to search disclosures:

- filer name
- description
- trade type
- transaction date
- amount

## Local Quick Start

Use this path when running locally.

1. Start the backend API and seed disclosure data by following [Local Development Workflow](./development-requirements.md#local-development-workflow).
2. Verify seeded results with the API examples below.
3. Open the frontend shell for browser verification with [Frontend Local Run Workflow](../frontend/README.md#local-run).

## API-First Search Examples

Use these commands from a terminal where the local API is available at `http://127.0.0.1:8000/api/v1`.

Search with filer name and description:

```bash
curl -sS "http://127.0.0.1:8000/api/v1/transactions?filer_name=Jane&description=Apple&page=1&page_size=10"
```

Search by trade type and date range:

```bash
curl -sS "http://127.0.0.1:8000/api/v1/transactions?trade_type=purchase&transaction_date_from=2026-01-01&transaction_date_to=2026-12-31&page=1&page_size=10"
```

Search by amount bucket text:

```bash
curl -sS "http://127.0.0.1:8000/api/v1/transactions?amount_text=%241%2C001%20-%20%2415%2C000&page=1&page_size=10"
```

Fetch one transaction and its filing context:

```bash
curl -sS "http://127.0.0.1:8000/api/v1/transactions/REPLACE_WITH_TRANSACTION_ID"
```

Fetch filing metadata directly:

```bash
curl -sS "http://127.0.0.1:8000/api/v1/filings/REPLACE_WITH_FILING_ID"
```

## Result Interpretation

- Trade type is normalized to a controlled value such as `purchase`, `sale`, or `exchange`.
- Transaction date is normalized when parsing succeeds.
- Amount is preserved as source bucket text and may include numeric bounds when derivable.
- Source PDF links remain available for verification.

## Provenance Verification Steps

1. Run a transaction search using one or more required fields.
2. Open a returned transaction record.
3. Read filing context and source links.
4. Open the source PDF link.
5. Confirm filer, description, trade type, transaction date, and amount match expected filing content.

## Browser Verification (Local Frontend)

Use the local frontend shell after backend setup and seeding.

1. Open `http://127.0.0.1:5173`.
2. Confirm loading state appears on the initial search request.
3. Apply filters and confirm table results update.
4. Open a result row to view transaction detail and filing context.
5. Open source links from results and detail views for provenance checks.

## Current Availability Notes

- The local path is API-first and supports browser verification through the frontend shell.
- Do not scrape OGE pages directly from the browser. Use backend ingestion and API endpoints.
- This guide remains valid as broader website UX is expanded because search and provenance verification stay API-driven.

## Troubleshooting

No results:

1. Confirm ingestion has run and jobs show completed status in `GET /api/v1/ingest/jobs`.
2. Broaden search filters and retry.
3. Confirm local API base URL and frontend API base URL configuration match.

Frontend data mismatch:

1. Confirm backend API is reachable at `http://127.0.0.1:8000/api/v1`.
2. Confirm `VITE_API_BASE_URL` points to the active backend when overridden.
3. Refresh the page to re-run API requests after backend seeding.
