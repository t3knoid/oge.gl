from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.infrastructure.ingestion_execution import IngestionJobExecutionCoordinator
from app.repositories.ingestion_jobs import CreateIngestionJobInput, IngestionJobRepository
from app.schemas.ingestion_jobs import IngestionJobAcceptedResponse, IngestionJobItem, IngestionJobListResponse


@dataclass
class IngestionRunCommand:
    mode: str = "incremental"
    limit: int | None = None
    force_reprocess: bool = False
    source_filters: dict | None = None


class IngestionJobExecutor(Protocol):
    def submit_job(self, job_id: UUID) -> object:
        ...


class IngestionJobService:
    def __init__(
        self,
        repository: IngestionJobRepository | None = None,
        executor: IngestionJobExecutor | None = None,
    ) -> None:
        self.repository = repository or IngestionJobRepository()
        self.executor = executor or IngestionJobExecutionCoordinator()

    def list_jobs(self, session: Session) -> IngestionJobListResponse:
        jobs = self.repository.list_jobs(session)
        return IngestionJobListResponse(
            items=[
                IngestionJobItem(
                    id=str(job.id),
                    job_type=job.job_type,
                    status=job.status,
                    requested_at=job.requested_at,
                    started_at=job.started_at,
                    finished_at=job.finished_at,
                    discovered_count=job.discovered_count,
                    downloaded_count=job.downloaded_count,
                    ingested_count=job.ingested_count,
                    warning_count=job.warning_count,
                    error_count=job.error_count,
                )
                for job in jobs
            ]
        )

    def create_job(self, session: Session, command: IngestionRunCommand) -> IngestionJobAcceptedResponse:
        job = self.repository.create_job(
            session,
            CreateIngestionJobInput(
                job_type=f"{command.mode}_ingest",
                mode=command.mode,
                force_reprocess=command.force_reprocess,
                source_filters=command.source_filters or {"type": "278 Transaction", "limit": command.limit},
            ),
        )
        self.executor.submit_job(job.id)
        return IngestionJobAcceptedResponse(
            job_id=str(job.id),
            status=job.status,
            accepted_at=job.requested_at,
        )
