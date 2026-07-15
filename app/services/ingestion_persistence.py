from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.repositories.ingestion_results import FilingUpsertInput, IngestionResultRepository, TransactionUpsertInput
from app.services.ingestion import FilingIngestionResult, IngestionWorkflowResult


@dataclass
class PersistenceIssue:
    code: str
    message: str
    severity: str
    external_id: str
    source_pdf_url: str


@dataclass
class PersistedIngestionSummary:
    downloaded_count: int
    ingested_count: int
    warning_count: int
    error_count: int
    issues: list[PersistenceIssue]


class IngestionPersistenceService:
    def __init__(self, repository: IngestionResultRepository | None = None) -> None:
        self.repository = repository or IngestionResultRepository()

    def persist_workflow_result(self, session: Session, workflow_result: IngestionWorkflowResult) -> PersistedIngestionSummary:
        downloaded_count = 0
        ingested_count = 0
        warning_count = workflow_result.skipped_missing_pdf_count
        error_count = 0
        issues: list[PersistenceIssue] = []

        for filing_result in workflow_result.filing_results:
            warning_count += len(filing_result.warnings)
            had_workflow_failure = filing_result.failure is not None
            if had_workflow_failure:
                error_count += 1

            if filing_result.source_pdf_url and filing_result.source_pdf_sha256:
                downloaded_count += 1

            if not filing_result.source_pdf_url or not filing_result.source_pdf_sha256:
                continue

            try:
                self._persist_filing_result(session, filing_result)
                session.commit()
            except Exception as exc:
                session.rollback()
                if not had_workflow_failure:
                    error_count += 1
                issues.append(
                    PersistenceIssue(
                        code="persistence_failed",
                        message=str(exc),
                        severity="error",
                        external_id=filing_result.external_id,
                        source_pdf_url=filing_result.source_pdf_url,
                    )
                )
                continue

            if not had_workflow_failure:
                ingested_count += 1

        return PersistedIngestionSummary(
            downloaded_count=downloaded_count,
            ingested_count=ingested_count,
            warning_count=warning_count,
            error_count=error_count,
            issues=issues,
        )

    def _persist_filing_result(self, session: Session, filing_result: FilingIngestionResult) -> None:
        existing_filing = self.repository.find_filing_by_identity(
            session,
            external_id=filing_result.external_id,
            source_pdf_url=filing_result.source_pdf_url,
            source_pdf_sha256=filing_result.source_pdf_sha256,
        )
        existing_transaction_count = 0
        if existing_filing is not None:
            existing_transaction_count = self.repository.count_transactions_for_filing(session, existing_filing.id)

        filing = self.repository.upsert_filing(
            session,
            existing_filing=existing_filing,
            payload=FilingUpsertInput(
                external_id=filing_result.external_id,
                filer_name=filing_result.filer_name,
                filer_title=filing_result.filer_title,
                agency=filing_result.agency,
                report_type=filing_result.report_type,
                filing_date=self._parse_date(filing_result.filing_date),
                source_page_url=filing_result.source_page_url,
                source_pdf_url=filing_result.source_pdf_url,
                source_pdf_sha256=filing_result.source_pdf_sha256,
                raw_metadata=filing_result.raw_metadata,
                ingest_status=self._determine_ingest_status(filing_result, existing_transaction_count),
                downloaded_at=datetime.now(timezone.utc),
                scraped_at=datetime.now(timezone.utc),
            ),
        )

        if filing_result.failure is not None:
            return

        self.repository.replace_transactions(
            session,
            filing_id=filing.id,
            transactions=[
                TransactionUpsertInput(
                    row_number=transaction.row_number,
                    description=transaction.description,
                    issuer_name=transaction.issuer_name,
                    trade_type=transaction.trade_type,
                    trade_type_raw=transaction.trade_type_raw,
                    transaction_date=self._parse_date(transaction.transaction_date),
                    transaction_date_raw=transaction.transaction_date_raw,
                    amount_text=transaction.amount_text,
                    amount_min=transaction.amount_min,
                    amount_max=transaction.amount_max,
                    raw_text=transaction.raw_text,
                )
                for transaction in filing_result.transactions
            ],
        )

    def _determine_ingest_status(self, filing_result: FilingIngestionResult, existing_transaction_count: int) -> str:
        if filing_result.failure is not None:
            return "partial" if existing_transaction_count > 0 else "failed"
        if filing_result.warnings:
            return "partial"
        return "completed"

    def _parse_date(self, value: str | None) -> date | None:
        if value is None:
            return None
        return date.fromisoformat(value)