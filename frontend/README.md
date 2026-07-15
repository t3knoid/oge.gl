# oge.gl Frontend

This directory contains the runnable React and TypeScript frontend shell for local development.

## Local Run

Use Node.js 22+.

```bash
cd frontend
npm install
npm run dev
```

The development server runs on the default Vite port (`http://127.0.0.1:5173`).

## Runtime Configuration

- `VITE_API_BASE_URL` (string): backend API root URL.
- Default value: `http://127.0.0.1:8000/api/v1`.

Example:

```bash
VITE_API_BASE_URL="http://127.0.0.1:8000/api/v1" npm run dev
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

## Scope Of This Slice

- Provides API-driven search and transaction detail routes.
- Provides labeled filter controls for filer name, description, trade type, transaction date, date range, and amount fields.
- Renders a transaction results table with filer, description, trade type, transaction date, amount, filing date, and source PDF columns.
- Renders transaction detail with filing context and provenance links from backend payload fields.
- Preserves filter, pagination, and sort state in URL query params for deterministic refresh and navigation behavior.
- Provides loading, empty, error, and paged result states for filtered queries.
- Keeps business logic and scraping behavior out of the browser.

## API Client

The frontend uses a centralized API client in `src/api/` for transactions list and detail calls plus filing detail calls.
UI routes consume this shared client so query serialization and error handling stay consistent across components.
