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
- `npm run lint`: run TypeScript-based lint gate.
- `npm run test`: run frontend smoke tests.

## Scope Of This Slice

- Provides route placeholders for search and transaction detail entry points.
- Provides baseline loading, empty, and error placeholders for API-driven pages.
- Keeps business logic and scraping behavior out of the browser.
