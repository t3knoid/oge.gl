# oge.gl Product Specification

## Purpose

`oge.gl` is a searchable web application for U.S. Office of Government Ethics transaction disclosures. The system ingests OGE Form 278-T PDFs, extracts normalized transaction records, stores them in a queryable data store, and exposes the data through an API consumed by a web frontend.

The primary user value is fast access to individual trade disclosures by filer, asset description, trade type, date, and amount without manually opening each PDF.

## Product Scope

The first development version should support the following end-to-end workflow:

1. Discover available OGE 278-T filings from the public OGE search page.
2. Download the linked PDF for each 278 Transaction result.
3. Scrape transaction rows from the PDF.
4. Normalize and persist filer and transaction data.
5. Provide an API for the frontend.
6. Allow users to search and filter the resulting dataset.
7. Preserve a link back to the original filing PDF for verification.

## Source Discovery Requirements

The authoritative discovery source is:

[https://www.oge.gov/web/OGE.nsf/Officials%20Individual%20Disclosures%20Search%20Collection?OpenForm](<https://www.oge.gov/web/OGE.nsf/Officials%20Individual%20Disclosures%20Search%20Collection?OpenForm>)

Discovery behavior:

1. The scraper workflow must query the OGE search interface for records where the `Type` field is `278 Transaction`.
2. Each search result row may contain a PDF link in the `Type` column.
3. The value `278 Transaction` in the `Type` column is the clickable link target to the source PDF.
4. The system should store both the result metadata and the resolved PDF URL.
5. The system should avoid duplicate ingestion of the same filing by tracking a stable external identifier or canonical PDF URL.

## Functional Requirements

### Required Search Fields

The application must allow users to search or filter scraped data by:

- filer name
- stock or asset name (`description`)
- trade type
- transaction date
- amount

### Record Visibility

Each transaction shown in the UI should expose at minimum:

- filer name
- filing date, if available
- report period, if available
- asset or issuer description
- trade type
- transaction date
- amount or amount range
- source PDF link
- source row text or extraction reference for auditability

### Result Behavior

1. Users should be able to combine filters.
2. Search should support partial text matching for filer name and description.
3. Search should support exact or normalized matching for trade type.
4. Date filtering should support either a single date or a date range.
5. Amount filtering should support exact bucket matching and optional range grouping if normalized numeric bounds are available.

## Proposed System Architecture

The project should be split into three layers:

1. Scraper service
2. API service
3. Frontend web application

### Suggested Repository Layout

```text
oge.gl/
  scraper/
    app/
    tests/
  api/
    app/
    tests/
  web/
    src/
  fixtures/
    pdfs/
  docs/
```

Suggested ownership by directory:

- `scraper/` contains source discovery, PDF download, parsing, normalization, and ingestion jobs
- `api/` contains the HTTP service and database-facing query layer
- `web/` contains the user-facing search interface
- `fixtures/pdfs/` contains sample 278-T filings used in tests
- `docs/` can hold deeper parser notes and schema decisions if the project grows

### Scraper Service Responsibilities

- discover filings from the OGE public search page
- download PDF source documents
- extract transaction rows from OGE Form 278-T PDFs
- normalize filer and transaction fields
- upsert records into the database
- track ingestion status, failures, and source provenance

### API Service Responsibilities

- expose searchable transaction records to the frontend
- provide filtering, pagination, and sorting
- return filer-level and filing-level metadata
- expose source document links and ingestion metadata

### Frontend Responsibilities

- render a search UI over transaction records
- provide filter controls for all required searchable fields
- show results in a table or list with pagination
- link each result back to the original PDF
- surface empty, loading, and error states clearly

## Data Model Specification

The normalized data model should separate filings from extracted transactions.

### Filing

Suggested fields:

- `id`
- `external_id`
- `filer_name`
- `filer_title` if available
- `agency` if available
- `report_type`
- `filing_date`
- `report_period_start` if available
- `report_period_end` if available
- `source_page_url`
- `source_pdf_url`
- `source_pdf_sha256`
- `downloaded_at`
- `scraped_at`
- `raw_metadata` JSON

### Transaction

Suggested fields:

- `id`
- `filing_id`
- `row_number`
- `description`
- `issuer_name` if derivable
- `trade_type`
- `transaction_date`
- `amount_text`
- `amount_min`
- `amount_max`
- `ownership_type` if available
- `commentary` if available
- `raw_text`
- `confidence_score` optional
- `created_at`
- `updated_at`

## Search Indexing Requirements

The backend should index at minimum:

- `filer_name`
- `description`
- `trade_type`
- `transaction_date`
- `amount_text`
- `amount_min`
- `amount_max`

Recommended database indexes:

- btree on `transaction_date`
- btree on `trade_type`
- btree on `amount_min` and `amount_max`
- trigram or full-text support on `filer_name` and `description`

## Scraping Specification

### Baseline Extraction Approach

The extraction layer should use `pdfplumber` as the primary parser. A baseline implementation may follow this approach:

```python
import pdfplumber
import re
from rapidfuzz import fuzz

ROW_RE = re.compile(r"^\s*(\d+)\s+(.+?)\s+(purchase|sale|unsolicited|solicited)", re.I)

def extract_rows(path):
    rows = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            for line in text.split("\n"):
                m = ROW_RE.match(line)
                if m:
                    num = int(m.group(1))
                    issuer = m.group(2).strip()
                    action = m.group(3).lower()
                    rows.append({
                        "num": num,
                        "issuer": issuer,
                        "action": action,
                        "raw": line
                    })
    return rows
```

This is a starting point only. Production extraction should extend it to capture all required fields and handle common OGE formatting inconsistencies.

### Extraction Requirements

1. The scraper must tolerate multi-page filings.
2. The scraper must tolerate line wrapping inside description fields.
3. The scraper must normalize trade type values into a controlled vocabulary.
4. The scraper must preserve the original raw line text for audit and debugging.
5. The scraper must support reprocessing previously downloaded PDFs when parser logic improves.

### Trade Type Normalization

Normalize extracted actions into a stable set such as:

- `purchase`
- `sale`
- `exchange`
- `unsolicited`
- `solicited`
- `other`

If the source document contains variants, the original text should still be preserved in the raw extraction payload.

### Amount Normalization

OGE filings often use amount buckets rather than exact values. The system should:

1. Store the source amount text exactly as shown.
2. Derive `amount_min` and `amount_max` where the filing uses a known range bucket.
3. Allow search by bucket text even when numeric normalization is not possible.

Example normalization:

- `$1,001 - $15,000` -> `amount_min=1001`, `amount_max=15000`
- `Over $1,000,000` -> `amount_min=1000000`, `amount_max=NULL`

### Date Normalization

1. Store the raw extracted date text when present.
2. Normalize transaction dates to ISO 8601 (`YYYY-MM-DD`) when parsing succeeds.
3. Flag rows for review when dates are missing or ambiguous.

## API Specification

The scraper service should persist data behind an API that the UI consumes.

### Suggested Endpoints

#### `GET /health`

Returns service health.

#### `GET /transactions`

Searches and filters transaction records.

Suggested query parameters:

- `filer_name`
- `description`
- `trade_type`
- `transaction_date`
- `transaction_date_from`
- `transaction_date_to`
- `amount_text`
- `amount_min`
- `amount_max`
- `page`
- `page_size`
- `sort`
- `order`

Suggested response shape:

```json
{
  "items": [
    {
      "id": "txn_123",
      "filer_name": "Jane Doe",
      "description": "Apple Inc.",
      "trade_type": "purchase",
      "transaction_date": "2026-05-08",
      "amount_text": "$1,001 - $15,000",
      "amount_min": 1001,
      "amount_max": 15000,
      "source_pdf_url": "https://example.gov/filing.pdf",
      "raw_text": "1 Apple Inc. purchase 05/08/2026 $1,001 - $15,000"
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 12345
}
```

#### `GET /transactions/:id`

Returns a single normalized transaction with filing metadata.

#### `GET /filings`

Returns filing-level data and source metadata.

#### `POST /ingest/run`

Triggers an ingestion job. This endpoint can be restricted to internal use.

#### `GET /ingest/jobs`

Returns ingestion job status, counts, and failures.

## Frontend Specification

### Core Screens

The first version only needs a focused search experience:

1. Search page
2. Results table
3. Transaction detail drawer or page

### Search Controls

Required controls:

- filer name text input
- stock or description text input
- trade type dropdown or multi-select
- transaction date picker or date range
- amount bucket text input or select
- reset filters action

### Results Table

Recommended columns:

- filer
- description
- trade type
- transaction date
- amount
- filing date
- source

The source column should link to the original PDF.

### UX Requirements

1. The initial page load should not require a PDF fetch from the browser.
2. Filtering should update results through the API only.
3. Loading, empty, and error states should be explicit.
4. URLs should preserve filter state when possible.

## Ingestion Workflow

Recommended ingestion stages:

1. discover result pages from the OGE search interface
2. extract result metadata and PDF links
3. deduplicate against existing filings
4. download PDFs
5. extract raw text and rows
6. normalize fields
7. upsert filing and transaction records
8. record success, warnings, and failures

## Error Handling Requirements

The system should explicitly handle:

- missing or broken PDF links
- PDF download failures
- image-only or poorly extractable PDFs
- partial row extraction
- duplicate filings
- source site layout changes

Failures should be logged with enough metadata to re-run individual filings.

## Operational Requirements

### Idempotency

Ingestion must be idempotent. Running the same ingestion job multiple times should not create duplicate filings or duplicate transactions.

### Auditability

Each normalized record should be traceable back to:

- source search result
- source PDF URL
- raw extracted line or page content

### Reprocessing

The system should support re-running extraction against previously stored PDFs after parser improvements.

## Testing Requirements

The project should include tests for:

1. PDF row extraction from known sample 278-T filings
2. normalization of amount buckets
3. normalization of transaction dates
4. search API filtering by each required field
5. combined filter behavior
6. duplicate filing prevention

At minimum, keep a small fixture set of representative 278-T PDFs covering:

- simple single-page filings
- multi-page filings
- wrapped descriptions
- varying amount formats

## Initial Milestones

### Milestone 1

- discover and download 278 Transaction PDFs
- extract a basic set of transaction rows
- persist filings and transactions in a local database

### Milestone 2

- expose a searchable API
- implement filterable frontend results
- add source PDF linking

### Milestone 3

- improve normalization accuracy
- add ingestion monitoring and job history
- add reprocessing support

## Out of Scope for First Version

- OCR for unreadable scanned PDFs unless source quality requires it
- advanced analytics or charting
- user accounts or authentication for public search
- manual annotation tools

## Summary

The development target for `oge.gl` is a three-part system that discovers OGE Form 278-T filings from the public OGE site, extracts transaction data from the linked PDFs using `pdfplumber`, stores normalized records, and exposes them through an API for a searchable frontend. The first version should optimize for correctness, provenance, and practical searchability rather than broad feature scope.
