from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class FilingRecord(BaseModel):
    id: str
    external_id: str | None = None
    filer_name: str
    filer_title: str | None = None
    agency: str | None = None
    filing_date: date | None = None
    report_period_start: date | None = None
    report_period_end: date | None = None
    source_page_url: str
    source_pdf_url: str
    ingest_status: str
    transaction_count: int | None = None


class FilingDetailResponse(FilingRecord):
    pass
