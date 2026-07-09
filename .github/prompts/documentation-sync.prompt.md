---
name: Documentation Sync
description: "Audit code changes and identify the exact documentation updates required for oge.gl, including product, development, prompt, and rule-file follow-through."
argument-hint: Describe the feature, branch, PR, or diff to audit for documentation updates
agent: agent
---

# oge.gl Documentation Sync Prompt

Review the current workspace changes and identify every documentation update required for oge.gl.

Mandatory instruction sources:

- `.github/copilot-instructions.md`
- `README.md`
- `docs/product-specification.md`
- `docs/development-requirements.md`
- `.cursor/rules/core.mdc`
- `.cursor/rules/docs.mdc`
- `.github/prompts/code-review.prompt.md`

If any required source is missing, say so explicitly.
Treat the existing repository documents as the source of truth unless the outgoing code change clearly requires those documents to be corrected.

Primary task:

- inspect the current code changes, affected files, and any related UI, scraper, API, or operational behavior
- determine which documentation must be updated so the docs stay accurate for developers, operators, reviewers, and future implementers

Focus areas:

- user-facing search behavior
- developer-facing setup, stack, and workflow behavior
- scraper discovery, PDF download, parsing, normalization, and reprocessing behavior
- API contract behavior, filtering, sorting, pagination, and error behavior
- database, provenance, idempotency, and duplicate-prevention behavior
- new or changed buttons, menus, search controls, navigation paths, loading states, empty states, and error states
- setup, configuration, deployment, or operational guidance
- environment variables, storage paths, ports, runtime defaults, and local development expectations
- prompt files and Cursor rule files when repository workflow expectations change

Check for required updates in places such as:

- [README.md](../../README.md)
- [docs/product-specification.md](../../docs/product-specification.md)
- [docs/development-requirements.md](../../docs/development-requirements.md)
- relevant files under the `docs/` tree
- `.github/prompts/*.prompt.md` when prompt behavior or review workflow expectations change
- `.cursor/rules/*.mdc` when repository rules, boundaries, or documentation routing change

For each required update:

1. Show the exact diff lines, changed behavior, or concrete evidence that triggered the documentation need.
2. Name the document that must be updated and explain why.
3. Propose the minimal documentation change in 1 to 3 sentences.
4. If the change introduces a new UI state, ingestion workflow, or operational workflow, propose a verification or QA scenario.
5. Implement the change in the relevant document.
6. When updating UI-facing documentation, describe the current interface directly.
7. Prefer present-tense expectations for controls, navigation, loading states, filtering behavior, and operational guidance.
8. Avoid framing docs as migrations from older behavior with wording such as `now`, `no longer`, `instead of`, or `rather than` unless the comparison is required for safety or release notes.

oge.gl-specific constraints:

- be evidence-based; do not suggest speculative documentation work
- preserve the OGE Form 278-T discovery and scraping workflow unless the audited change explicitly updates that specification
- any product behavior change affecting searchable fields, source-discovery behavior, provenance expectations, or API-facing search behavior must update `docs/product-specification.md` in the same change
- any stack, environment, workflow, service-boundary, deployment, or operational change must update `docs/development-requirements.md` in the same change
- keep `README.md` concise and aligned with the deeper docs it links to
- keep terminology consistent across filer, filing, transaction, description, trade type, transaction date, amount, and source PDF references
- prefer small targeted edits over broad rewrites
- keep recommendations modular, concise, contributor-friendly, and easy to scan
- if no update is needed for an area, say so briefly

Return findings in exactly this structure:

#### Required Documentation Updates

- Group by document or feature area.

#### Suggested Verification Or QA Additions

- Include manual verification scenarios when relevant.

#### Suggested Prompt Or Rule Updates

- Include prompt or Cursor rule follow-up only when workflow expectations changed.

#### Confidence (High / Medium / Low)

- Give a short reason for the confidence level.
