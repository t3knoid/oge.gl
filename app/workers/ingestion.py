from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.ingestion_jobs import IngestionJobRepository
from app.services.ingestion import IngestionWorkflowService
from app.services.ingestion_persistence import IngestionPersistenceService


logger = logging.getLogger(__name__)


@dataclass
class WorkerRunResult:
    job_id: UUID
    status: str
    discovered_count: int
    downloaded_count: int
    ingested_count: int
    warning_count: int
    error_count: int


class IngestionWorkerService:
    def __init__(
        self,
        *,
        repository: IngestionJobRepository | None = None,
        workflow_service: IngestionWorkflowService | None = None,
        persistence_service: IngestionPersistenceService | None = None,
    ) -> None:
        self.repository = repository or IngestionJobRepository()
        self.workflow_service = workflow_service or IngestionWorkflowService()
        self.persistence_service = persistence_service or IngestionPersistenceService()

    def run_next_job(self, session: Session) -> WorkerRunResult | None:
        job = self.repository.claim_next_job(session)
        if job is None:
            return None

        self.repository.add_event(
            session,
            job_id=job.id,
            event_type="job_started",
            severity="info",
            message="Started queued ingestion job.",
            event_metadata={"mode": job.mode},
        )

        try:
            limit = job.source_filters.get("limit") if isinstance(job.source_filters, dict) else None
            workflow_result = self.workflow_service.ingest_discovered_filings(limit=limit)
            persistence_summary = self.persistence_service.persist_workflow_result(session, workflow_result)

            for filing_result in workflow_result.filing_results:
                for warning in filing_result.warnings:
                    self.repository.add_event(
                        session,
                        job_id=job.id,
                        event_type="filing_warning",
                        severity="warning",
                        message=warning.message,
                        event_metadata={
                            "code": warning.code,
                            "external_id": filing_result.external_id,
                            "source_pdf_url": filing_result.source_pdf_url,
                            "raw_text": warning.raw_text,
                        },
                    )

                if filing_result.failure is not None:
                    self.repository.add_event(
                        session,
                        job_id=job.id,
                        event_type="filing_failed",
                        severity="error",
                        message=filing_result.failure.message,
                        event_metadata={
                            "stage": filing_result.failure.stage,
                            "code": filing_result.failure.code,
                            "external_id": filing_result.external_id,
                            "source_pdf_url": filing_result.source_pdf_url,
                        },
                    )

            for issue in persistence_summary.issues:
                self.repository.add_event(
                    session,
                    job_id=job.id,
                    event_type="filing_persistence_failed",
                    severity=issue.severity,
                    message=issue.message,
                    event_metadata={
                        "code": issue.code,
                        "external_id": issue.external_id,
                        "source_pdf_url": issue.source_pdf_url,
                    },
                )

            warning_count = persistence_summary.warning_count
            error_count = persistence_summary.error_count
            status = "completed"
            if warning_count > 0 or error_count > 0:
                status = "partial"

            self.repository.mark_job_finished(
                session,
                job_id=job.id,
                status=status,
                discovered_count=workflow_result.discovered_count,
                downloaded_count=persistence_summary.downloaded_count,
                ingested_count=persistence_summary.ingested_count,
                warning_count=warning_count,
                error_count=error_count,
            )
            self.repository.add_event(
                session,
                job_id=job.id,
                event_type="job_finished",
                severity="info",
                message="Discovery execution finished for queued ingestion job.",
                event_metadata={
                    "discovered_count": workflow_result.discovered_count,
                    "skipped_missing_pdf_count": workflow_result.skipped_missing_pdf_count,
                    "downloaded_count": persistence_summary.downloaded_count,
                    "ingested_count": persistence_summary.ingested_count,
                    "error_count": error_count,
                    "warning_count": warning_count,
                },
            )
            logger.info("ingestion_job_finished", extra={"job_id": str(job.id), "status": status})
            return WorkerRunResult(
                job_id=job.id,
                status=status,
                discovered_count=workflow_result.discovered_count,
                downloaded_count=persistence_summary.downloaded_count,
                ingested_count=persistence_summary.ingested_count,
                warning_count=warning_count,
                error_count=error_count,
            )
        except Exception as exc:
            self.repository.mark_job_finished(
                session,
                job_id=job.id,
                status="failed",
                discovered_count=0,
                downloaded_count=0,
                ingested_count=0,
                warning_count=0,
                error_count=1,
                last_error_code="worker_execution_failed",
                last_error_message=str(exc),
            )
            self.repository.add_event(
                session,
                job_id=job.id,
                event_type="job_failed",
                severity="error",
                message="Queued ingestion job failed during worker execution.",
                event_metadata={"error_code": "worker_execution_failed"},
            )
            logger.exception("ingestion_job_failed", extra={"job_id": str(job.id)})
            return WorkerRunResult(
                job_id=job.id,
                status="failed",
                discovered_count=0,
                downloaded_count=0,
                ingested_count=0,
                warning_count=0,
                error_count=1,
            )
