---
name: Implement Ticket
description: "Implement an oge.gl ticket with a root-cause fix, focused tests, verification, pattern reuse, and documentation review."
argument-hint: "Paste the ticket, acceptance criteria, issue text, or subsystem"
agent: "agent"
---

# oge.gl - Unified Ticket Implementation Prompt

Implement the provided ticket in the oge.gl repository.

Use the user argument as the source of truth for the requested behavior, acceptance criteria, or problem scope.

This prompt includes documentation-audit and documentation-update requirements as part of implementation. Treat documentation review as a required deliverable whenever behavior, API contracts, operations, workflow expectations, or UI expectations change.

-------------------------------------------------------------------------------
## Mandatory instruction sources
-------------------------------------------------------------------------------

Read and apply all of the following before any analysis, planning, code edits, or test changes:

- `.github/copilot-instructions.md`
- `README.md`
- `docs/product-specification.md`
- `docs/development-requirements.md`
- `.cursor/rules/core.mdc`
- `.cursor/rules/backend.mdc`
- `.cursor/rules/frontend.mdc`
- `.cursor/rules/shell-docker.mdc`
- `.cursor/rules/docs.mdc`
- `.github/prompts/code-review.prompt.md`
- `.github/prompts/documentation-sync.prompt.md`
- `.github/prompts/scaffold-ticket.prompt.md`

Treat these repository documents as the single source of truth.
Do not restate or loosen them.
If one of them is missing, say so explicitly.

-------------------------------------------------------------------------------
## Pattern Discovery and DRY Enforcement (Mandatory)
-------------------------------------------------------------------------------

Before writing any code, you must perform a repository-wide pattern discovery step.

### 1. Search for existing patterns

Identify and inspect the closest existing implementation that solves a similar problem, including:

- API routes, request and response models, and error-handling patterns
- service-layer logic for validation, ingestion orchestration, normalization, deduplication, and reprocessing behavior
- infrastructure wrappers for HTTP fetching, PDF download, file storage, and background work
- data models, migration patterns, and indexed query paths
- React components, layouts, centralized API client usage, and search/filter UI patterns
- transaction listing, filtering, pagination, and source-PDF linking flows
- logging, diagnostics, and operational patterns
- test patterns for API, services, parser behavior, malformed input, duplicate ingestion, and migrations

### 2. Enforce DRY

You must avoid DRY violations:

- do not duplicate logic, schemas, components, services, or error contracts
- do not introduce new abstractions if an equivalent one already exists
- do not create new browser-side scraping logic when backend or scraper ownership is required
- if you introduce a new pattern, justify why reuse is not possible

### 3. Reuse existing contracts and patterns

You must reuse:

- existing API contracts and error response patterns
- existing schema and validation boundaries
- existing service ownership and router thinness
- existing infrastructure wrappers and async handoff patterns
- existing frontend UI patterns and API client usage
- existing test structure and fixtures

Match the closest existing implementation in:

- structure
- naming
- validation
- error handling
- observability
- async safety
- UI behavior
- testing style

If the ticket requires a new variant, explain why the existing one cannot be reused.

-------------------------------------------------------------------------------
## Scope routing
-------------------------------------------------------------------------------

Apply repository rules by file and behavior scope:

- `.github/copilot-instructions.md`: always-on rules for architecture boundaries, validation discipline, testing expectations, and safe implementation behavior
- `docs/product-specification.md`: product behavior, required search fields, source discovery, provenance expectations, and API-facing search behavior
- `docs/development-requirements.md`: stack, local setup, service boundaries, workflow, and operational guidance
- `.cursor/rules/core.mdc`: global provenance, trust-boundary, logging, and validation rules
- `.cursor/rules/backend.mdc`: scraper, API, persistence, normalization, ingestion, and backend validation rules
- `.cursor/rules/frontend.mdc`: frontend behavior, accessibility, filter state, API usage, and UI validation rules
- `.cursor/rules/shell-docker.mdc`: shell, Docker, Compose, subprocess, and environment-handling safety
- `.cursor/rules/docs.mdc`: documentation scope, sync expectations, and writing constraints
- `.github/prompts/code-review.prompt.md`: review priorities to preserve during implementation, especially correctness, provenance, regressions, and test completeness

When a changed file falls under multiple instruction sources, apply all relevant rules together.

-------------------------------------------------------------------------------
## Implementation goals
-------------------------------------------------------------------------------

Your job is to:

- restate the ticket clearly before coding
- investigate the current implementation and identify the root cause or missing behavior
- perform pattern discovery and reuse existing patterns and contracts
- implement the smallest complete change that satisfies the request
- keep the solution aligned with oge.gl architecture, provenance, and safety rules
- add or update automated tests for the changed behavior
- verify the change with the relevant checks before declaring success
- inspect affected files and behavior to identify required documentation updates
- implement the necessary documentation changes in the relevant documents

If the ticket affects product behavior, searchable fields, source-discovery behavior, provenance expectations, or API-facing behavior, `docs/product-specification.md` must be updated in the same change.

If the ticket affects stack, workflow, environment, deployment, service boundaries, or operational behavior, `docs/development-requirements.md` must be updated in the same change.

If the ticket conflicts with repository instructions, do not implement the conflicting behavior.
Explain the conflict and propose a compliant alternative.

-------------------------------------------------------------------------------
## oge.gl-specific invariants
-------------------------------------------------------------------------------

These rules must remain true unless the ticket explicitly changes the specification and the documentation is updated accordingly:

- the system discovers OGE Form 278-T filings from the public OGE search surface
- `278 Transaction` results remain the intended discovery target
- the PDF link remains tied to the `Type` column behavior described in the product specification
- normalized transactions remain traceable back to source filing metadata and source PDFs
- ingestion remains idempotent and duplicate-safe under retry
- raw extraction context remains available where needed for auditability and debugging
- trade type, date, and amount normalization remain deterministic and contract-aligned where parsing is possible
- the frontend remains API-driven and does not scrape the source site directly
- scraper, API, persistence, and frontend responsibilities remain clearly separated

-------------------------------------------------------------------------------
## Documentation sync requirements
-------------------------------------------------------------------------------

Review the current workspace changes and identify every documentation update required for oge.gl.

Primary task:

- inspect the changed code, affected files, and related scraper, API, UI, or operational behavior
- determine which documents must be updated so docs remain accurate for developers, operators, reviewers, and future implementers

Focus areas:

- user-facing search behavior
- developer-facing setup or run behavior
- environment keys, defaults, expected value types, or runtime config behavior
- architectural behavior or trust-boundary changes
- request and response contracts
- validation rules and error messages
- ingestion, duplicate-prevention, provenance, and reprocessing behavior
- new or changed UI states, filters, buttons, loading states, empty states, and error states

Check for required updates in places such as:

- `README.md`
- `docs/product-specification.md`
- `docs/development-requirements.md`
- files under `docs/`
- prompt files when implementation workflow expectations change
- Cursor rule files when repository rules or routing change

For each required update:

1. Show the exact diff lines, changed behavior, or concrete evidence that triggered the documentation need.
2. Name the document that must be updated and explain why.
3. Propose the minimal documentation change in 1 to 3 sentences.
4. If the change introduces a new UI state or workflow, propose a verification scenario.
5. Implement the change in the relevant document.

Documentation constraints:

- be evidence-based and avoid speculative documentation work
- keep edits small, targeted, and contributor-friendly
- prefer current-behavior documentation over historical wording
- if no documentation update is needed for an area, say so briefly

-------------------------------------------------------------------------------
## Required workflow
-------------------------------------------------------------------------------

1. Summarize the ticket and list assumptions.
2. Identify which instruction sources apply to the touched files.
3. Perform pattern discovery and list the existing patterns and contracts you will reuse.
4. Read the relevant code, tests, and docs.
5. If schema changes are required, inspect current models and migration history before editing.
6. Identify the root cause with evidence.
7. Describe instruction compliance before coding, including trust boundaries, service ownership, safe error handling, provenance handling, and migration fidelity when applicable.
8. Add or update focused tests first when practical.
9. Implement the minimal root-cause fix using the identified existing patterns.
10. Audit the changed behavior for required documentation updates using concrete evidence.
11. Implement the minimal required documentation updates in the relevant documents.
12. Run the relevant verification steps.
13. Report what changed and whether the ticket now appears complete.
14. State whether documentation is aligned or which documents and comments needed updates and why.

If the request is unclear or under-specified, ask a small number of focused questions instead of guessing.

-------------------------------------------------------------------------------
## Output format
-------------------------------------------------------------------------------

## Ticket Understanding
Short summary of the requested behavior.

## Instruction Compliance
Explain how the planned change respects repository instructions, including trust boundaries, service ownership, safe error handling, provenance handling, and migration workflow where applicable.

## Pattern Reuse Plan
List the existing patterns, contracts, and abstractions being reused.

## Root Cause
What is broken, missing, or risky.

## Implementation
Bullet list of the changes made.

## Tests and Verification
List the tests or checks run and the outcomes. Do not claim success without fresh verification evidence.

#### Required Documentation Updates
- Group by document or feature area.

#### Suggested Verification Additions
- Include manual verification scenarios when relevant.

#### Confidence (High / Medium / Low)
- Give a short reason for the confidence level.

## Notes
Any remaining risks, follow-ups, assumptions, instruction conflicts, or documentation updates still needed.
