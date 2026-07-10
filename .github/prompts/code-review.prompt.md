---
name: Code Review
description: "Perform a code review of local outgoing changes not yet synced to origin using oge.gl repository instructions and prompt rules, including required documentation and test follow-up."
argument-hint: "Describe the feature, local outgoing change set, ticket, or risk areas to review"
agent: agent
---

# oge.gl Code Review Prompt

Use this prompt to run a focused review of the local outgoing oge.gl change set that has not yet been synced to `origin`.

Default review scope:

- local commits ahead of the tracked upstream branch, or `origin/main` when the upstream branch is `origin/main`
- local uncommitted tracked changes when they are part of the user-requested outgoing work

Do not default to reviewing historical merged work, `HEAD` in isolation, or generic repository state when there is no outgoing delta.
If there are no local outgoing changes, say so explicitly and stop after reporting that there is no change set to review.

## Context

- Feature summary:
  {{feature_summary}}
- Changed files: {{changed_files}}
- Related issue/ticket:
  {{ticket_reference}}
- Risk notes from author:
  {{author_risks}}

## Review Objectives

Perform a rigorous code review with findings ordered by severity.
Prioritize correctness, provenance, ingestion safety, data integrity, search behavior, API contract stability, and test completeness.
Treat documentation gaps and missing test follow-up as real findings when the outgoing change requires them.

## Required Checks

1. Architecture boundaries
   - Routers remain thin and only handle request parsing, validation, auth, pagination parsing, and response mapping.
   - Business logic is in services, not route handlers or frontend components.
   - Repositories or persistence helpers only handle data access, not business rules.
   - External I/O, file operations, PDF download, and OS-level behavior stay behind infrastructure boundaries when those abstractions exist.

2. OGE source discovery and ingestion behavior
   - Discovery logic still targets OGE `278 Transaction` results correctly.
   - PDF link extraction remains aligned with the `Type` column behavior described in the product docs.
   - Ingestion is idempotent and does not create duplicate filings or transactions on retry.
   - Partial failures, retries, and reprocessing behavior are explicit and safe.

3. Parsing, normalization, and provenance
   - PDF parsing tolerates multi-page filings, wrapped descriptions, and inconsistent layouts where relevant.
   - Raw extracted text or equivalent provenance context is preserved where needed for auditability.
   - Trade type normalization remains controlled and stable.
   - Transaction date normalization remains deterministic and safe for ambiguous inputs.
   - Amount bucket handling preserves source text and numeric derivation behavior where applicable.

4. API contract and search behavior
   - Search filters for filer name, description, trade type, transaction date, and amount remain supported where required.
   - Combined filtering, sorting, and pagination behavior remain deterministic.
   - Response models do not leak unsafe internals.
   - Contract-affecting changes are reflected in docs and tests.

5. Security and input safety
   - All user input, remote HTML, and PDF-derived content are treated as untrusted input.
   - Path, URL, header, query, and file-handling inputs are validated and normalized.
   - No raw exceptions, secrets, internal paths, or unsafe OS details leak through logs or API responses.
   - No unsafe subprocess, shell-string, or file-path behavior is introduced.

6. Persistence, schema, and indexing
   - Filing and transaction storage still preserves provenance and duplicate-prevention requirements.
   - Schema and index choices support the documented search paths.
   - Migrations, models, and queries remain aligned.
   - Upsert behavior is concurrency-safe where relevant.

7. Frontend behavior and trust boundary
   - The frontend remains API-driven and does not scrape the source site directly.
   - UI filters still map cleanly to backend-supported search fields.
   - Loading, empty, and error states are present where changed behavior requires them.
   - Source PDF links remain accessible and accurate where the UI exposes filing data.

8. Configuration and operational controls
   - New environment variables, defaults, ports, or storage expectations are documented.
   - No environment-specific constants are hardcoded without justification.
   - Download, storage, or deployment changes remain reproducible and operationally safe.

9. Testing quality
   - Python backend and scraper tests use `pytest`.
   - Unit tests cover service logic, parser behavior, and normalization changes.
   - API tests cover filtering, pagination, negative cases, and contract-sensitive behavior.
   - Frontend tests cover changed filter behavior and result rendering where relevant.
   - Edge cases such as missing fields, malformed PDFs, ambiguous dates, duplicate ingestion, and empty results are addressed where the change makes them relevant.

10. Documentation and follow-through
   - `README.md` remains a concise entrypoint and stays aligned with deeper docs.
   - `docs/product-specification.md` stays aligned with product behavior, required search fields, source-discovery expectations, and API-facing behavior.
   - `docs/development-requirements.md` stays aligned with stack, local workflow, service boundaries, and environment expectations.
   - Review findings must call out any required documentation updates needed to keep repository docs accurate.
   - Review findings must call out any missing or inadequate tests needed to support the recommended fix.

## Output Format

1. Findings
   - Severity: Critical | High | Medium | Low
   - File and line reference
   - Why this is a risk
   - Minimal fix recommendation
   - Required documentation updates, if any
   - Required test updates, if any
2. Open questions or assumptions
3. Test gaps
4. Brief change summary (only after findings)

## Hard Rules for Reviewer Output

- If no issues are found, state: "No findings identified."
- If there are no local outgoing changes not yet synced to `origin`, state that explicitly and do not invent a review scope.
- Do not rewrite large sections unless required for a fix suggestion.
- Keep focus on defects, regressions, and missing tests over style-only comments.
- When a finding implies documentation or test follow-up, name the affected document or test surface directly instead of leaving the recommendation implicit.
