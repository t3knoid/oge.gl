---
name: Fix Review Findings
description: "Resolve issues identified in a recent oge.gl review with root-cause fixes, focused validation, and required documentation sync."
argument-hint: "Paste the review findings, PR comments, issue list, or review summary to address"
agent: agent
---

# oge.gl Review Findings Resolution Prompt

Use this prompt to fix issues identified during a recent review of oge.gl.

Use the user argument as the source of truth for the findings to address.
Treat each finding as a concrete defect, regression risk, or test or documentation gap unless the user explicitly marks it as non-actionable.

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

Treat these repository documents as the single source of truth.
Do not restate or loosen them.
If one of them is missing, say so explicitly.

-------------------------------------------------------------------------------
## Review-fix goals
-------------------------------------------------------------------------------

Your job is to:

- restate the review findings you are going to fix
- confirm which findings are reproducible, already fixed, blocked, or invalid
- identify the root cause for each actionable finding
- implement the smallest complete fix that resolves the actual defect
- preserve oge.gl architecture boundaries and provenance requirements
- add or update focused tests for each fixed issue when practical
- re-run the narrowest checks that prove the finding is resolved
- update documentation when the fix changes product behavior, API behavior, setup, operations, or UI expectations
- update `docs/product-specification.md` when the fix changes searchable fields, source-discovery behavior, provenance expectations, or API-facing behavior
- update `docs/development-requirements.md` when the fix changes stack, workflow, environment, service-boundary, or operational expectations
- provide a concise summary of the change suitable for use as a commit message

If a reported finding is incorrect, outdated, or no longer reproducible, say so with concrete evidence rather than silently skipping it.

-------------------------------------------------------------------------------
## Pattern Discovery and DRY Enforcement (Mandatory)
-------------------------------------------------------------------------------

Before writing code, perform targeted pattern discovery around each finding.

Inspect the nearest existing implementation for:

- API routes, response models, and error handling patterns
- service-layer validation, ingestion orchestration, and normalization logic
- persistence, migration, and indexing conventions
- infrastructure wrappers for HTTP, file storage, PDF download, or subprocess behavior
- React UI behavior and centralized API client usage
- existing tests that cover adjacent behavior
- documentation and prompt updates for related workflow expectations

You must:

- reuse existing contracts and patterns where possible
- avoid duplicate fixes or one-off abstractions
- justify any new pattern introduced to fix a finding

-------------------------------------------------------------------------------
## oge.gl-specific invariants
-------------------------------------------------------------------------------

Unless the reviewed change explicitly alters the specification and the docs are updated accordingly, these rules remain true:

- the system discovers OGE Form 278-T filings from the public OGE search surface
- `278 Transaction` results remain the intended discovery target
- the PDF link remains tied to the `Type` column behavior described in the product specification
- normalized transactions remain traceable back to source filing metadata and source PDFs
- ingestion remains idempotent and duplicate-safe under retry
- raw extraction context remains available where needed for auditability and debugging
- trade type, date, and amount normalization remain deterministic and contract-aligned where parsing is possible
- the frontend remains API-driven and does not scrape the source site directly
- any product behavior or API-facing behavior change must update `docs/product-specification.md`
- any workflow, environment, service-boundary, or operational change must update `docs/development-requirements.md`

-------------------------------------------------------------------------------
## Required workflow
-------------------------------------------------------------------------------

1. Summarize the findings and list any assumptions.
2. Identify which findings are actionable, already fixed, blocked, or invalid.
3. Identify which instruction sources apply to the touched files.
4. Perform pattern discovery near each finding and list the patterns you will reuse.
5. Read the relevant code, tests, prompts, rules, and docs.
6. Reproduce or otherwise validate each finding with evidence when feasible.
7. Identify the root cause for each finding you will fix.
8. Describe instruction compliance before coding, including architecture boundaries, provenance safety, error handling, and documentation obligations.
9. Add or update focused tests first when practical.
10. Implement the minimal root-cause fixes.
11. Audit the changed behavior for required documentation updates.
12. Run the relevant verification steps.
13. Report which findings are fixed, which remain open, and why.
14. End with a concise change summary that can be reused as a commit message. Present the commit message in imperative or past-tense style inside a code block.

If the user supplied multiple findings, address them in severity order unless there is a clear dependency that requires a different order.

If a finding cannot be fixed safely without more context, ask a small number of focused questions instead of guessing.

-------------------------------------------------------------------------------
## Documentation sync requirements
-------------------------------------------------------------------------------

Review the fixes for any required documentation updates.

Check for updates in places such as:

- `README.md`
- `docs/product-specification.md`
- `docs/development-requirements.md`
- files under `docs/`
- `.github/prompts/*.prompt.md` when workflow expectations changed
- `.cursor/rules/*.mdc` when repository rules or routing changed

For each required update:

1. Show the concrete evidence that triggered the documentation need.
2. Name the document that must change and explain why.
3. Make the minimal documentation edit needed to keep docs accurate.

Keep documentation edits present-tense, evidence-based, and narrowly scoped.

-------------------------------------------------------------------------------
## Output format
-------------------------------------------------------------------------------

## Findings Addressed
List the review findings you handled in this pass.

## Instruction Compliance
Explain how the fixes respect repository rules, including architecture boundaries, provenance safety, error handling, and documentation obligations.

## Pattern Reuse Plan
List the existing patterns, contracts, and abstractions reused for the fixes.

## Root Cause
Describe the actual cause of each actionable finding.

## Implementation
Bullet list of the fixes made.

## Tests and Verification
List the checks run and their outcomes. Do not claim a finding is fixed without fresh evidence.

#### Required Documentation Updates
- Group by document or feature area.

#### Remaining Findings or Blockers
- List any review findings not fixed in this pass and explain why.

#### Confidence (High / Medium / Low)
- Give a short reason for the confidence level.

## Notes
Include follow-ups, assumptions, invalidated findings, or residual risks.

## Commit Message Summary
Provide 1 concise sentence in imperative or past-tense style inside a fenced code block that summarizes the change set and can be used directly or adapted for a git commit message.
