from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.ingestion_jobs import IngestionJobRepository
from app.workers.discovery import DiscoveryWorkflowResult, DiscoveryWorkflowService


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
        workflow_service: DiscoveryWorkflowService | None = None,
    ) -> None:
        self.repository = repository or IngestionJobRepository()
        self.workflow_service = workflow_service or DiscoveryWorkflowService()

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
            workflow_result = self.workflow_service.run_incremental_discovery(limit=limit)
            warning_count = workflow_result.skipped_missing_pdf_count
            status = "partial" if warning_count > 0 else "completed"

            self.repository.mark_job_finished(
                session,
                job_id=job.id,
                status=status,
                discovered_count=workflow_result.discovered_count,
                downloaded_count=0,
                ingested_count=0,
                warning_count=warning_count,
                error_count=0,
            )
            self.repository.add_event(
                session,
                job_id=job.id,
                event_type="job_finished",
                severity="info",
                message="Discovery execution finished for queued ingestion job.",
                event_metadata={
                    "discovered_count": workflow_result.discovered_count,
                    "eligible_count": len(workflow_result.eligible_records),
                    "skipped_missing_pdf_count": workflow_result.skipped_missing_pdf_count,
                },
            )
            logger.info("ingestion_job_finished", extra={"job_id": str(job.id), "status": status})
            return WorkerRunResult(
                job_id=job.id,
                status=status,
                discovered_count=workflow_result.discovered_count,
                downloaded_count=0,
                ingested_count=0,
                warning_count=warning_count,
                error_count=0,
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
