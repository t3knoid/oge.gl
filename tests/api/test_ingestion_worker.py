from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Filing, IngestionJob, IngestionJobEvent, Transaction
from app.repositories.ingestion_jobs import IngestionJobRepository
from app.repositories.ingestion_results import IngestionResultRepository
from app.services.ingestion import (
    FilingIngestionResult,
    IngestionWorkflowResult,
    NormalizedTransactionResult,
    WorkflowFailure,
    WorkflowWarning,
)
from app.services.ingestion_persistence import IngestionPersistenceService
from app.workers.ingestion import IngestionWorkerService


def _sqlite_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)()


class StubWorkflowService:
    def ingest_discovered_filings(self, *, limit: int | None = None) -> IngestionWorkflowResult:
        filing_results = [_successful_filing_result(with_warning=False)]
        if limit is not None:
            filing_results = filing_results[:limit]
        return IngestionWorkflowResult(
            discovered_count=1,
            filing_results=filing_results,
            skipped_missing_pdf_count=0,
            failed_count=0,
        )


class FailingWorkflowService:
    def ingest_discovered_filings(self, *, limit: int | None = None) -> IngestionWorkflowResult:
        raise RuntimeError("upstream discovery failed")


class StubIngestionWorkflowService:
    def __init__(self, result: IngestionWorkflowResult) -> None:
        self.result = result

    def ingest_discovered_filings(self, *, limit: int | None = None) -> IngestionWorkflowResult:
        return self.result


class JobFinishFailingRepository(IngestionJobRepository):
    def __init__(self) -> None:
        self.failed_once = False

    def mark_job_finished(
        self,
        session: Session,
        *,
        job_id,
        status: str,
        discovered_count: int,
        downloaded_count: int,
        ingested_count: int,
        warning_count: int,
        error_count: int,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
    ):
        if not self.failed_once:
            self.failed_once = True
            raise RuntimeError("job status write failed")
        return super().mark_job_finished(
            session,
            job_id=job_id,
            status=status,
            discovered_count=discovered_count,
            downloaded_count=downloaded_count,
            ingested_count=ingested_count,
            warning_count=warning_count,
            error_count=error_count,
            last_error_code=last_error_code,
            last_error_message=last_error_message,
        )


class JobFinishIntegrityFailingRepository(IngestionJobRepository):
    def __init__(self) -> None:
        self.failed_once = False

    def mark_job_finished(
        self,
        session: Session,
        *,
        job_id,
        status: str,
        discovered_count: int,
        downloaded_count: int,
        ingested_count: int,
        warning_count: int,
        error_count: int,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
    ):
        if not self.failed_once:
            self.failed_once = True
            session.add(
                Filing(
                    external_id="oge:test-filing",
                    filer_name="Duplicate",
                    filer_title="Duplicate",
                    agency="Duplicate",
                    report_type="278T",
                    filing_date=None,
                    source_page_url="https://www.oge.gov/search",
                    source_pdf_url="https://www.oge.gov/files/one.pdf",
                    source_pdf_sha256="a" * 64,
                    raw_metadata={},
                    ingest_status="failed",
                )
            )
            session.flush()
        return super().mark_job_finished(
            session,
            job_id=job_id,
            status=status,
            discovered_count=discovered_count,
            downloaded_count=downloaded_count,
            ingested_count=ingested_count,
            warning_count=warning_count,
            error_count=error_count,
            last_error_code=last_error_code,
            last_error_message=last_error_message,
        )


class DuplicateInsertOnceRepository(IngestionResultRepository):
    def __init__(self) -> None:
        self.returned_miss_once = False

    def find_filing_by_identity(
        self,
        session: Session,
        *,
        external_id: str,
        source_pdf_url: str,
        source_pdf_sha256: str,
    ) -> Filing | None:
        if not self.returned_miss_once:
            self.returned_miss_once = True
            return None
        return super().find_filing_by_identity(
            session,
            external_id=external_id,
            source_pdf_url=source_pdf_url,
            source_pdf_sha256=source_pdf_sha256,
        )


class DuplicateTransactionOnceRepository(IngestionResultRepository):
    def __init__(self) -> None:
        self.failed_once = False

    def replace_transactions(
        self,
        session: Session,
        *,
        filing_id,
        transactions,
    ) -> None:
        if not self.failed_once:
            self.failed_once = True
            raise IntegrityError("duplicate transaction", params=None, orig=Exception("unique violation"))
        return super().replace_transactions(session, filing_id=filing_id, transactions=transactions)


def _successful_filing_result(*, with_warning: bool = True) -> FilingIngestionResult:
    warnings = []
    if with_warning:
        warnings = [
            WorkflowWarning(
                code="missing_transaction_date",
                message="A transaction row is missing a transaction date.",
                raw_text="2 Microsoft Corp. Sale Over $50,000,000",
            )
        ]

    return FilingIngestionResult(
        external_id="oge:test-filing",
        filer_name="Trump, Donald J",
        filer_title="President",
        agency="White House Office",
        filing_date="2026-07-01",
        filing_date_raw="07/01/2026",
        report_type="278T",
        source_page_url="https://www.oge.gov/search",
        source_pdf_url="https://www.oge.gov/files/one.pdf",
        source_pdf_sha256="a" * 64,
        raw_metadata={
            "filing_date_raw": "07/01/2026",
            "position": "President",
            "type_label": "278 Transaction",
            "level": "n/a",
        },
        transactions=[
            NormalizedTransactionResult(
                row_number=1,
                description="Apple Inc.",
                issuer_name="Apple Inc.",
                trade_type="purchase",
                trade_type_raw="Purchase",
                transaction_date="2026-06-30",
                transaction_date_raw="06/30/2026",
                amount_text="$1,001 - $15,000",
                amount_min=1001,
                amount_max=15000,
                raw_text="1 Apple Inc. Purchase 06/30/2026 $1,001 - $15,000",
            ),
            NormalizedTransactionResult(
                row_number=2,
                description="Microsoft Corp.",
                issuer_name="Microsoft Corp.",
                trade_type="sale",
                trade_type_raw="Sale",
                transaction_date=None,
                transaction_date_raw=None,
                amount_text="Over $50,000,000",
                amount_min=50000000,
                amount_max=None,
                raw_text="2 Microsoft Corp. Sale Over $50,000,000",
            ),
        ],
        warnings=warnings,
    )


def _failed_filing_result() -> FilingIngestionResult:
    return FilingIngestionResult(
        external_id="oge:failed-filing",
        filer_name="Trump, Donald J",
        filer_title="President",
        agency="White House Office",
        filing_date="2026-07-02",
        filing_date_raw="07/02/2026",
        report_type="278T",
        source_page_url="https://www.oge.gov/search",
        source_pdf_url="https://www.oge.gov/files/two.pdf",
        source_pdf_sha256="b" * 64,
        raw_metadata={
            "filing_date_raw": "07/02/2026",
            "position": "President",
            "type_label": "278 Transaction",
            "level": "n/a",
        },
        transactions=[],
        warnings=[],
        failure=WorkflowFailure(stage="parse", code="parse_failed", message="The PDF did not yield any parsed transaction rows."),
    )


def test_worker_claims_and_completes_next_job() -> None:
    session = _sqlite_session()
    job = IngestionJob(
        job_type="incremental_ingest",
        mode="incremental",
        status="queued",
        requested_at=datetime.now(),
        force_reprocess=False,
        source_filters={"type": "278 Transaction", "limit": 10},
    )
    session.add(job)
    session.commit()

    worker = IngestionWorkerService(workflow_service=StubWorkflowService())

    result = worker.run_next_job(session)

    refreshed = session.get(IngestionJob, job.id)
    events = list(session.scalars(select(IngestionJobEvent).where(IngestionJobEvent.job_id == job.id)))

    assert result is not None
    assert result.status == "succeeded"
    assert refreshed is not None
    assert refreshed.status == "succeeded"
    assert refreshed.discovered_count == 1
    assert refreshed.downloaded_count == 1
    assert refreshed.ingested_count == 1
    assert refreshed.warning_count == 0
    assert len(events) == 2
    assert {event.event_type for event in events} == {"job_started", "job_finished"}

    session.close()


def test_worker_marks_failures_and_records_error_event() -> None:
    session = _sqlite_session()
    job = IngestionJob(
        job_type="incremental_ingest",
        mode="incremental",
        status="queued",
        requested_at=datetime.now(),
        force_reprocess=False,
        source_filters={"type": "278 Transaction"},
    )
    session.add(job)
    session.commit()

    worker = IngestionWorkerService(workflow_service=FailingWorkflowService())

    result = worker.run_next_job(session)

    refreshed = session.get(IngestionJob, job.id)
    events = list(session.scalars(select(IngestionJobEvent).where(IngestionJobEvent.job_id == job.id)))

    assert result is not None
    assert result.status == "failed"
    assert refreshed is not None
    assert refreshed.status == "failed"
    assert refreshed.error_count == 1
    assert refreshed.last_error_code == "worker_execution_failed"
    assert len(events) == 2
    assert {event.event_type for event in events} == {"job_started", "job_failed"}

    session.close()


def test_worker_persists_filings_transactions_and_job_counters() -> None:
    session = _sqlite_session()
    job = IngestionJob(
        job_type="incremental_ingest",
        mode="incremental",
        status="queued",
        requested_at=datetime.now(),
        force_reprocess=False,
        source_filters={"type": "278 Transaction", "limit": 10},
    )
    session.add(job)
    session.commit()

    worker = IngestionWorkerService(
        workflow_service=StubIngestionWorkflowService(
            IngestionWorkflowResult(
                discovered_count=2,
                filing_results=[_successful_filing_result(), _failed_filing_result()],
                skipped_missing_pdf_count=1,
                failed_count=1,
            )
        )
    )

    result = worker.run_next_job(session)

    refreshed = session.get(IngestionJob, job.id)
    filings = list(session.scalars(select(Filing)))
    transactions = list(session.scalars(select(Transaction).order_by(Transaction.row_number)))

    assert result is not None
    assert result.status == "failed"
    assert result.discovered_count == 2
    assert result.downloaded_count == 2
    assert result.ingested_count == 1
    assert result.warning_count == 2
    assert result.error_count == 1

    assert refreshed is not None
    assert refreshed.status == "failed"
    assert refreshed.discovered_count == 2
    assert refreshed.downloaded_count == 2
    assert refreshed.ingested_count == 1
    assert refreshed.warning_count == 2
    assert refreshed.error_count == 1
    assert refreshed.last_error_code is None

    assert len(filings) == 2
    assert filings[0].external_id == "oge:test-filing"
    assert {filing.ingest_status for filing in filings} == {"partial", "failed"}
    assert len(transactions) == 2
    assert transactions[0].description == "Apple Inc."
    assert transactions[1].raw_text == "2 Microsoft Corp. Sale Over $50,000,000"

    session.close()


def test_worker_reingestion_keeps_persistence_idempotent() -> None:
    session = _sqlite_session()

    first_job = IngestionJob(
        job_type="incremental_ingest",
        mode="incremental",
        status="queued",
        requested_at=datetime.now(),
        force_reprocess=False,
        source_filters={"type": "278 Transaction", "limit": 10},
    )
    second_job = IngestionJob(
        job_type="incremental_ingest",
        mode="incremental",
        status="queued",
        requested_at=datetime.now(),
        force_reprocess=False,
        source_filters={"type": "278 Transaction", "limit": 10},
    )
    session.add(first_job)
    session.add(second_job)
    session.commit()

    worker = IngestionWorkerService(
        workflow_service=StubIngestionWorkflowService(
            IngestionWorkflowResult(
                discovered_count=1,
                filing_results=[_successful_filing_result()],
                skipped_missing_pdf_count=0,
                failed_count=0,
            )
        )
    )

    first_result = worker.run_next_job(session)
    second_result = worker.run_next_job(session)

    filings = list(session.scalars(select(Filing)))
    transactions = list(session.scalars(select(Transaction)))

    assert first_result is not None
    assert second_result is not None
    assert len(filings) == 1
    assert len(transactions) == 2
    assert first_result.ingested_count == 1
    assert second_result.ingested_count == 1

    session.close()


def test_worker_preserves_partial_counts_when_job_finalization_fails() -> None:
    session = _sqlite_session()
    job = IngestionJob(
        job_type="incremental_ingest",
        mode="incremental",
        status="queued",
        requested_at=datetime.now(),
        force_reprocess=False,
        source_filters={"type": "278 Transaction", "limit": 10},
    )
    session.add(job)
    session.commit()

    worker = IngestionWorkerService(
        repository=JobFinishFailingRepository(),
        workflow_service=StubIngestionWorkflowService(
            IngestionWorkflowResult(
                discovered_count=1,
                filing_results=[_successful_filing_result()],
                skipped_missing_pdf_count=0,
                failed_count=0,
            )
        ),
    )

    result = worker.run_next_job(session)

    refreshed = session.get(IngestionJob, job.id)
    filings = list(session.scalars(select(Filing)))
    transactions = list(session.scalars(select(Transaction)))

    assert result is not None
    assert result.status == "failed"
    assert result.discovered_count == 1
    assert result.downloaded_count == 1
    assert result.ingested_count == 1
    assert result.warning_count == 1
    assert result.error_count == 1

    assert refreshed is not None
    assert refreshed.status == "failed"
    assert refreshed.discovered_count == 1
    assert refreshed.downloaded_count == 1
    assert refreshed.ingested_count == 1
    assert refreshed.warning_count == 1
    assert refreshed.error_count == 1
    assert refreshed.last_error_code == "worker_execution_failed"
    assert len(filings) == 1
    assert len(transactions) == 2

    session.close()


def test_worker_rolls_back_failed_session_before_manual_job_fallback() -> None:
    session = _sqlite_session()
    job = IngestionJob(
        job_type="incremental_ingest",
        mode="incremental",
        status="queued",
        requested_at=datetime.now(),
        force_reprocess=False,
        source_filters={"type": "278 Transaction", "limit": 10},
    )
    session.add(job)
    session.commit()

    worker = IngestionWorkerService(
        repository=JobFinishIntegrityFailingRepository(),
        workflow_service=StubIngestionWorkflowService(
            IngestionWorkflowResult(
                discovered_count=1,
                filing_results=[_successful_filing_result()],
                skipped_missing_pdf_count=0,
                failed_count=0,
            )
        ),
    )

    result = worker.run_next_job(session)

    refreshed = session.get(IngestionJob, job.id)
    events = list(session.scalars(select(IngestionJobEvent).where(IngestionJobEvent.job_id == job.id)))

    assert result is not None
    assert result.status == "failed"
    assert result.discovered_count == 1
    assert result.downloaded_count == 1
    assert result.ingested_count == 1
    assert result.warning_count == 1
    assert result.error_count == 1

    assert refreshed is not None
    assert refreshed.status == "failed"
    assert refreshed.discovered_count == 1
    assert refreshed.downloaded_count == 1
    assert refreshed.ingested_count == 1
    assert refreshed.warning_count == 1
    assert refreshed.error_count == 1
    assert refreshed.last_error_code == "worker_execution_failed"
    assert {event.event_type for event in events} == {"job_started", "job_failed", "filing_warning"}

    session.close()


def test_duplicate_filing_conflict_is_treated_as_idempotent_reload() -> None:
    session = _sqlite_session()

    repository = DuplicateInsertOnceRepository()
    existing_filing = Filing(
        external_id="oge:test-filing",
        filer_name="Trump, Donald J",
        filer_title="President",
        agency="White House Office",
        report_type="278T",
        filing_date=None,
        source_page_url="https://www.oge.gov/search",
        source_pdf_url="https://www.oge.gov/files/one.pdf",
        source_pdf_sha256="a" * 64,
        raw_metadata={"existing": True},
        ingest_status="completed",
    )
    session.add(existing_filing)
    session.commit()

    summary = IngestionPersistenceService(repository=repository).persist_workflow_result(
        session,
        IngestionWorkflowResult(
            discovered_count=1,
            filing_results=[_successful_filing_result()],
            skipped_missing_pdf_count=0,
            failed_count=0,
        ),
    )

    filings = list(session.scalars(select(Filing)))
    transactions = list(session.scalars(select(Transaction).order_by(Transaction.row_number)))

    assert summary.downloaded_count == 1
    assert summary.ingested_count == 1
    assert summary.warning_count == 1
    assert summary.error_count == 0
    assert summary.issues == []
    assert len(filings) == 1
    assert len(transactions) == 2
    assert filings[0].raw_metadata["position"] == "President"
    assert transactions[0].description == "Apple Inc."

    session.close()


def test_duplicate_transaction_conflict_is_retried_idempotently() -> None:
    session = _sqlite_session()

    existing_filing = Filing(
        external_id="oge:test-filing",
        filer_name="Trump, Donald J",
        filer_title="President",
        agency="White House Office",
        report_type="278T",
        filing_date=None,
        source_page_url="https://www.oge.gov/search",
        source_pdf_url="https://www.oge.gov/files/one.pdf",
        source_pdf_sha256="a" * 64,
        raw_metadata={"existing": True},
        ingest_status="completed",
    )
    session.add(existing_filing)
    session.commit()

    summary = IngestionPersistenceService(repository=DuplicateTransactionOnceRepository()).persist_workflow_result(
        session,
        IngestionWorkflowResult(
            discovered_count=1,
            filing_results=[_successful_filing_result()],
            skipped_missing_pdf_count=0,
            failed_count=0,
        ),
    )

    filings = list(session.scalars(select(Filing)))
    transactions = list(session.scalars(select(Transaction).order_by(Transaction.row_number)))

    assert summary.downloaded_count == 1
    assert summary.ingested_count == 1
    assert summary.warning_count == 1
    assert summary.error_count == 0
    assert summary.issues == []
    assert len(filings) == 1
    assert len(transactions) == 2
    assert transactions[0].description == "Apple Inc."
    assert transactions[1].raw_text == "2 Microsoft Corp. Sale Over $50,000,000"

    session.close()
