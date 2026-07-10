from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.filings import FilingRepository
from app.schemas.filings import FilingDetailResponse, FilingRecord


class FilingService:
    def __init__(self, repository: FilingRepository | None = None) -> None:
        self.repository = repository or FilingRepository()

    def get_filing(self, session: Session, filing_id: UUID) -> FilingDetailResponse | None:
        result = self.repository.get_filing(session, filing_id)
        if result is None:
            return None

        filing = result.filing
        return FilingDetailResponse(
            id=str(filing.id),
            external_id=filing.external_id,
            filer_name=filing.filer_name,
            filer_title=filing.filer_title,
            agency=filing.agency,
            filing_date=filing.filing_date,
            report_period_start=filing.report_period_start,
            report_period_end=filing.report_period_end,
            source_page_url=filing.source_page_url,
            source_pdf_url=filing.source_pdf_url,
            ingest_status=filing.ingest_status,
            transaction_count=result.transaction_count,
        )
