from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import IngestionJob, IngestionJobEvent
from app.workers.discovery import DiscoveryRecord, DiscoveryWorkflowResult
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
    def run_incremental_discovery(self, *, limit: int | None = None) -> DiscoveryWorkflowResult:
        records = [
            DiscoveryRecord(
                filing_date="07/01/2026",
                position="President",
                type_label="278 Transaction",
                filer_name="Trump, Donald J",
                agency="White House Office",
                level="n/a",
                source_page_url="https://www.oge.gov/search",
                source_pdf_url="https://www.oge.gov/files/one.pdf",
            )
        ]
        if limit is not None:
            records = records[:limit]
        return DiscoveryWorkflowResult(discovered_count=1, eligible_records=records, skipped_missing_pdf_count=0)


class FailingWorkflowService:
    def run_incremental_discovery(self, *, limit: int | None = None) -> DiscoveryWorkflowResult:
        raise RuntimeError("upstream discovery failed")


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
    assert result.status == "completed"
    assert refreshed is not None
    assert refreshed.status == "completed"
    assert refreshed.discovered_count == 1
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
