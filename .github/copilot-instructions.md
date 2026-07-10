# Copilot Instructions for oge.gl

## 0. Rule Priority and Working Mode

1. Follow this priority order when instructions overlap:
   - data integrity, provenance, trust boundaries, and safe handling of untrusted external input
   - architecture boundaries, reproducible ingestion behavior, and idempotent persistence
   - task requirements and established repository patterns
   - tests and validation
   - style and tooling
2. Prefer the smallest correct change.
3. Inspect nearby code before changing patterns.
4. Preserve existing abstractions unless restructuring is explicitly required.
5. Add or update focused tests for changed behavior.
6. Validate the narrowest affected surface first.
7. Match existing architectural, API, and documentation patterns.
8. Do not refactor unrelated code or change public behavior unless required.

## 1. Project Intent

This project is oge.gl, a searchable application for U.S. Office of Government Ethics transaction disclosures.
The system discovers OGE Form 278-T filings, downloads source PDFs, extracts transaction data, stores normalized records, and exposes those records through an API and frontend search interface.

The primary project goals are:

- accurate discovery of public OGE 278-T filings
- reliable PDF parsing and normalization
- traceability from normalized records back to source documents
- searchable transaction records by filer name, description, trade type, transaction date, and amount
- clear separation between scraper, API, persistence, and frontend responsibilities

## 2. Core Architecture Rules

1. Keep strict separation of concerns.
2. API routers are thin and handle request parsing, validation, auth, response mapping, pagination parsing, and delegation only.
3. Services own business logic, normalization, deduplication, ingestion orchestration, reprocessing behavior, and lifecycle rules.
4. Infrastructure handles external HTTP access, PDF download, file storage, subprocess wrappers, and other OS-level behavior.
5. Persistence handles database access only.
6. The frontend is untrusted and must never be treated as a source of truth.
7. No business logic in frontend components.
8. Services and routers must not call low-level OS or subprocess primitives directly when an infrastructure boundary is appropriate.

## 3. Primary Stack Expectations

1. Scraper and API: Python 3.12+.
2. API: FastAPI, Pydantic, SQLAlchemy or SQLModel, and Uvicorn.
3. Scraper parsing: `pdfplumber` with supporting normalization helpers such as `rapidfuzz` where justified.
4. Frontend: React with TypeScript.
5. Database: PostgreSQL in production, SQLite only where appropriate for tests or local experimentation.
6. Async safety is required in request handlers.
7. Long-running work such as batch ingestion or large PDF processing must be offloaded from request handlers.

## 4. OGE Domain Principles

1. The authoritative source-discovery surface is the public OGE disclosures search page documented in `docs/product-specification.md`.
2. Discovery targets `278 Transaction` results from the OGE search interface unless the specification is explicitly changed.
3. The PDF link is derived from the `Type` column behavior described in the product specification.
4. Every normalized filing and transaction record must preserve enough provenance to trace back to the source filing and source PDF.
5. Unknown, incomplete, or inconsistent PDF layouts must be handled defensively.
6. Parsing and normalization improvements must not require redownloading all source data when stored PDFs can be reused.
7. Duplicate prevention must be deterministic where source identity permits it.

## 5. Security and Safety

1. Treat all remote HTML, PDF content, and user-supplied query parameters as untrusted input.
2. Validate and normalize all path, file, URL, header, and query inputs.
3. Prevent traversal, injection, malformed-input, and unsafe file-path behavior.
4. Never use dynamic code execution.
5. Use explicit subprocess argument arrays only when subprocess use is required.
6. Do not leak internal stack traces, absolute paths, credentials, or secrets in API responses.
7. Do not leak raw exception strings, unsafe OS details, or private infrastructure details in logs, API responses, or documentation.
8. Downloaded files must be written only to validated storage locations.
9. External HTTP access must use explicit timeouts and structured error handling.

## 6. Provenance and Auditability Model

1. Normalized transactions must remain traceable back to source filing metadata and source PDFs.
2. Raw extraction text or equivalent provenance context must be preserved where needed for auditability and parser debugging.
3. Logs and diagnostics must support investigation of download failures, parse failures, normalization warnings, and duplicate-prevention behavior.
4. Public-facing responses must expose source links intentionally and safely.

## 7. Logging and Observability

1. Use structured logs with clear event names and context fields.
2. Log discovery outcomes, download failures, parse failures, normalization warnings, and ingestion upsert counts.
3. Do not log raw secrets or unsafe local paths.
4. Keep correlation or request identifiers across API, service, and background-task layers where relevant.
5. Do not rely only on unhandled-exception logging; handled failures, degraded behavior, retries, and logic inconsistencies must be logged where detected.

## 8. Reliability and Data Lifecycle

1. Ingestion must be idempotent.
2. Retry-safe persistence paths are required.
3. Handle partial failures explicitly.
4. Reprocessing of previously stored PDFs must remain possible when parser behavior improves.
5. Ensure listing and search behavior remain deterministic under concurrency.
6. Bound concurrency for ingestion, parsing, and cleanup work.

## 9. API and Schema Standards

1. Use explicit request and response models for all API bodies.
2. Define consistent safe error responses across endpoints.
3. Document each endpoint with expected query parameters, response fields, and failure behavior when the API surface exists.
4. Keep filtering behavior explicit and deterministic.
5. Keep listing behavior stable, with explicit sort order and documented pagination expectations.
6. Search behavior must support the documented required fields: filer name, description, trade type, transaction date, and amount.

## 10. Frontend Standards

1. All HTTP calls go through a centralized API client when such a client exists.
2. Do not hardcode API origins in components.
3. Surface safe, user-readable loading, empty, and error states.
4. Use accessible controls for filtering, searching, and source-link interaction.
5. Avoid storing derived state when it can be computed.
6. Frontend code must not expose raw exceptions, absolute paths, or internal-only infrastructure details.
7. Frontend code must not scrape the OGE source site directly.

## 11. Testing Requirements

1. Every new behavior should include tests when practical.
2. Backend tests should use `pytest`.
3. Add unit tests for services, parser behavior, and validation logic.
4. Add API tests for filtering, listing, retrieval, and negative cases.
5. Add integration tests for ingestion flows where behavior crosses service boundaries.
6. Add migration tests when schema changes are introduced.
7. Add frontend accessibility, filter-behavior, and error-surface tests when frontend behavior changes.
8. Add tests for malformed or inconsistent source input when the changed behavior depends on parser robustness.

## 12. Migration and Data Change Rules

1. Migrations must reflect model changes exactly.
2. Migrations should be reversible whenever feasible.
3. Avoid schema drift between models and migration history.
4. Include indexes for the documented high-traffic query paths such as filer name, description, trade type, transaction date, and amount filtering.
5. Preserve provenance and duplicate-prevention requirements in schema design.

## 13. Documentation Rules

1. Write documentation in present tense focused on current behavior.
2. Write documentation in non-time-relative language; prefer scope-based wording over chronology-based wording such as `now`, `currently`, `first`, `future`, or `no longer` unless time sequencing is genuinely required.
3. Avoid historical wording that compares old and new behavior unless necessary.
4. Keep setup and operational docs accurate for local and production-like environments.
5. Update comments and nearby documentation in the same change when behavior changes.
6. Keep `README.md` concise and aligned with deeper docs.
7. Treat `docs/product-specification.md` as the canonical source for product behavior, source-discovery behavior, searchable fields, provenance expectations, and API-facing behavior.
8. Treat `docs/development-requirements.md` as the canonical source for stack, workflow, environment, service-boundary, and operational expectations.
9. Any change to product behavior, searchable fields, source-discovery behavior, provenance expectations, or API-facing behavior must update `docs/product-specification.md` in the same change.
10. Any change to stack, environment, workflow, deployment, service boundaries, or operational behavior must update `docs/development-requirements.md` in the same change.

## 14. Code Review Priorities

1. Correctness under malformed or inconsistent source input.
2. Provenance preservation and auditability.
3. Duplicate prevention and idempotent ingestion.
4. Search correctness and API contract stability.
5. Observability quality and actionable logs.
6. Test completeness and regression coverage.

## 15. Assistant Behavior Expectations

1. Prefer small, safe, reviewable changes.
2. Preserve architectural boundaries.
3. Reuse existing patterns before introducing new abstractions.
4. When uncertain, favor the documented OGE workflow over speculative behavior.
5. Never introduce browser-side scraping or undocumented source assumptions unless explicitly requested.
6. Keep shell, subprocess, Docker, Compose, and environment-handling changes aligned with documented stack and operational expectations.

## 16. oge.gl Normative Product Rules

1. Search and filtering must support filer name, description, trade type, transaction date, and amount.
2. Source PDF links must remain available for result verification when filing data is exposed.
3. Amount bucket text should be preserved exactly as sourced when available.
4. Numeric amount bounds may be derived when parsing is reliable.
5. Transaction dates should normalize to ISO 8601 when parsing succeeds while preserving raw text when ambiguity matters.
6. Trade types should normalize into a controlled vocabulary while preserving raw text where needed.

## 17. Shell, Subprocess, Docker, and Compose Rules

1. Use explicit argument lists for subprocess calls; do not use `shell=True`.
2. Route application subprocess behavior through infrastructure wrappers.
3. Quote shell variable expansions and use `set -euo pipefail` in Bash scripts.
4. Do not parse `.env` files with unsafe splitting or echo secrets in scripts.
5. Pin container base images to specific versions where practical and prefer multi-stage builds for production images.
6. Production images must avoid unnecessary packages, embedded secrets, and root execution unless explicitly required and documented.
7. Shell, container, and Compose changes must update environment and operational docs when documented defaults change.
