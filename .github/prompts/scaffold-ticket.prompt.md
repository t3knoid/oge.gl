---
name: Scaffold Ticket
description: "Generate a scoped, implementation-ready oge.gl GitHub issue from a feature request, issue summary, or subsystem change."
argument-hint: "Paste the feature request, acceptance criteria, issue text, or subsystem to turn into a build-ready ticket"
agent: agent
---

# oge.gl Ticket Scaffolding Prompt

Use this prompt to generate one scoped implementation ticket for oge.gl.

Use the user argument as the source of truth for the requested behavior, acceptance criteria, subsystem, or engineering need.

Treat the following repository documents as the source of truth when shaping the ticket:

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
- `.github/prompts/fix-review-findings.prompt.md`

If one of these sources is missing, say so explicitly.

## Goal

Draft one implementation issue that is specific, testable, documentation-aware, and ready for engineering work.

Create the GitHub issue in the current repository by using the `gh` CLI tool after drafting the issue content.

The issue must preserve clear architecture boundaries, provenance requirements, idempotent ingestion behavior, and the documented split between scraper, API, and frontend responsibilities.

## GitHub Issue Creation Requirements

- Before creating a new issue, search for an existing open GitHub issue with the same or materially similar title using the `gh` CLI.
- Prefer a non-interactive duplicate check such as `gh issue list --search <title>` or an equivalent `gh` search command scoped to the current repository.
- If a matching open issue already exists, report that issue to the user and do not create a duplicate unless the user explicitly asks for a separate issue.
- After drafting the issue title and body, create the issue in the current repository with a non-interactive `gh issue create` command.
- Use the `gh` CLI through the terminal tool; do not stop after only drafting the issue text when issue creation is possible.
- Prefer a non-interactive form such as `gh issue create --title <title> --body-file <file>` or an equivalent safe non-interactive variant.
- If `gh` is unavailable, the user is not authenticated, or issue creation fails for an environment reason you cannot resolve safely, say so explicitly and return the ready-to-submit issue title and body.
- After successful creation, include the created issue number and URL in the final response.

## Issue shaping rules

- Keep scraper, API, persistence, and frontend responsibilities separated.
- Keep routers thin and business logic in services.
- Preserve the OGE Form 278-T discovery model unless the request explicitly changes the spec.
- Preserve source PDF provenance and traceability requirements.
- Preserve idempotent ingestion and duplicate-prevention behavior.
- Keep the frontend API-driven and do not push scraping logic into the browser.
- Require documentation updates whenever behavior, API shape, configuration, operations, workflow expectations, or UI expectations change.
- Require `docs/product-specification.md` updates whenever product behavior, searchable fields, source-discovery behavior, provenance expectations, or API-facing behavior change.
- Require `docs/development-requirements.md` updates whenever stack, environment, workflow, service-boundary, deployment, or operational expectations change.
- Avoid environment-specific or implementation-specific assumptions unless the request explicitly requires them.

## Required sections to produce

### 1. Summary

One short paragraph describing the feature, problem, and expected outcome.

### 2. Scope

- In scope
- Out of scope

### 3. Functional Requirements

Include the relevant requirements from the repository docs, tailored to the request. Cover the applicable areas below.

1. Source discovery and ingestion rules
   - OGE Form 278-T discovery behavior when relevant
   - `278 Transaction` search targeting when relevant
   - source PDF resolution, provenance, and traceability expectations
   - idempotent ingestion, retry behavior, and duplicate-prevention expectations
2. Parsing and normalization behavior
   - PDF parsing expectations for multi-page and inconsistent layouts when relevant
   - trade type normalization expectations
   - transaction date normalization expectations
   - amount bucket handling expectations
3. Search and API behavior
   - filer name, description, trade type, transaction date, and amount filtering where relevant
   - sorting, pagination, and deterministic listing behavior
   - safe error behavior and contract expectations
4. Frontend behavior
   - API-driven search behavior
   - filter controls, results rendering, and source PDF linking when UI is affected
   - loading, empty, and error states when relevant
5. Provenance, auditability, and operations
   - traceability from normalized records back to source documents
   - logging and diagnostics expectations when relevant
   - reprocessing behavior when the change touches parser or ingestion workflow

### 4. Non-Functional Requirements

- Performance expectations
- Reliability and concurrency expectations
- Security expectations
- Observability and logging expectations
- Accessibility or responsive behavior expectations when UI is affected

### 5. API Contract Changes

- Endpoints added or changed
- Request or response shape changes
- Error behavior or status code changes
- Filtering, sorting, pagination, or auth behavior changes

### 6. Data Model and Migration Impact

- Tables, columns, or indexes affected
- Migration requirements
- Reversibility notes
- Provenance and duplicate-prevention implications
- Future compatibility notes when relevant

### 7. Configuration Changes

- New or updated environment keys
- Default values
- Expected value types
- Operational notes and rollout considerations

### 8. Acceptance Criteria

Provide a numbered list of verifiable criteria written as observable outcomes.

### 9. Test Plan

At minimum include the applicable items below:

- unit tests for services, parser behavior, and validation
- API tests for happy path and negative cases
- integration tests for ingestion or persistence behavior when relevant
- migration tests when schema changes occur
- frontend coverage when UI behavior changes
- edge-case tests for malformed source data, ambiguous dates, duplicate ingestion, or empty results when relevant

### 10. Documentation Impact

- Documents that must be updated
- Why each document needs an update
- Minimal doc changes required
- Verification or QA additions if UI or workflow behavior changes

If the ticket changes product or API-facing behavior, this section must explicitly include `docs/product-specification.md`.
If the ticket changes stack, environment, workflow, deployment, or service-boundary behavior, this section must explicitly include `docs/development-requirements.md`.

### 11. Risks and Mitigations

- Top technical risks
- Mitigation plan for each

### 12. Rollout and Verification

- Rollout steps
- Post-deploy or post-merge checks
- Suggested verification commands, as applicable

Suggested verification commands, as applicable:

- `pytest`
- migration commands when schema changes are involved
- frontend lint or test commands
- focused API checks or scraper dry-run commands when relevant

### 13. Open Questions

Call out unknowns explicitly when the request is underspecified.

## Output constraints

- Keep the ticket concise but implementation-ready.
- Use present tense.
- Prefer small, reviewable slices over multi-system rewrites.
- Be explicit about documentation work when behavior changes.
- Do not invent unsupported workflow or infrastructure details unless the request explicitly requires them.
- When issue creation succeeds, report the final GitHub issue number and URL after the issue content summary.
