# oge.gl Frontend

This directory contains the runnable React and TypeScript frontend shell for local development.

## Local Run

Use Node.js 22+.

Prerequisite: run database migrations, start the backend API, and seed at least one ingestion run by following the local ingestion workflow in [docs/development-requirements.md](../docs/development-requirements.md#local-development-workflow).

```bash
cd frontend
npm install
npm run dev
```

The development server runs on the default Vite port (`http://127.0.0.1:5173`).

## Browser Verification

1. Open `http://127.0.0.1:5173` and confirm an initial loading state appears.
2. Trigger the manual fetch control and confirm the UI reports accepted ingestion job status.
3. Apply a filter that returns no records and confirm the empty state message is shown.
4. Apply combined filters and confirm the results table updates with backend data.
5. Verify source PDF links in the results table open backend-provided provenance targets.
6. Open a transaction detail route and confirm filing context plus source links render.
7. Use reset filters and confirm the default query reloads.
8. Refresh the page and confirm URL query parameters restore the same filtered view.

Unsupported local verification path:

1. Running the frontend shell without a reachable backend API is not a supported end-to-end verification flow.

## Runtime Configuration

- `VITE_API_BASE_URL` (string): backend API root URL.
- Default value in local development: `http://127.0.0.1:8000/api/v1`.
- Default value in deployed builds served by the backend: `/api/v1`.

Manual fetch defaults are backend-owned and are read by the frontend through `GET /api/v1/ingest/defaults`.

Example:

```bash
VITE_API_BASE_URL="http://127.0.0.1:8000/api/v1" npm run dev
```

When the frontend is built into the backend image, browser requests to `/` and frontend application routes are served by FastAPI and the frontend calls the colocated API through the relative `/api/v1` base URL.

Manual fetch prerequisite:

```bash
VITE_API_BASE_URL="http://127.0.0.1:8000/api/v1" \
npm run dev
```

## Available Scripts

- `npm run dev`: start local frontend dev server.
- `npm run build`: typecheck and build production assets.
- `npm run preview`: preview the production build locally.
- `npm run typecheck`: run TypeScript checks.
- `npm run lint`: run the typecheck gate (alias to `npm run typecheck`).
- `npm run test`: run frontend smoke tests.
- `npm run audit`: run a full dependency audit.
- `npm run audit:prod`: run a production-dependency audit.

## CI Baseline

Use this command sequence for deterministic frontend checks in CI:

```bash
npm ci
npm run lint
npm run test
npm run build
```

## Scope Of This Slice

- Provides API-driven search and transaction detail routes.
- Provides labeled filter controls for filer name, description, trade type, transaction date, date range, and amount fields.
- Renders a transaction results table with filer, description, trade type, transaction date, amount, filing date, and source PDF columns.
- Renders transaction detail with filing context and provenance links from backend payload fields.
- Preserves filter, pagination, and sort state in URL query params for deterministic refresh and navigation behavior.
- Provides loading, empty, error, and paged result states for filtered queries.
- Provides a manual fetch control that submits an ingestion run through the backend API and reports accepted or failed submission state.
- Keeps business logic and scraping behavior out of the browser.

## API Client

The frontend uses a centralized API client in `src/api/` for transactions list and detail calls plus filing detail calls.
UI routes consume this shared client so query serialization and error handling stay consistent across components.
