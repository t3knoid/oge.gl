from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.models import IngestionJob, IngestionJobEvent


@dataclass
class CreateIngestionJobInput:
    job_type: str
    mode: str
    force_reprocess: bool
    source_filters: dict
    requested_by: str | None = None


class IngestionJobRepository:
    def list_jobs(self, session: Session) -> list[IngestionJob]:
        return list(session.scalars(select(IngestionJob).order_by(IngestionJob.requested_at.desc(), IngestionJob.id)))

    def get_job(self, session: Session, job_id: UUID) -> IngestionJob | None:
        return session.get(IngestionJob, job_id)

    def list_job_events(self, session: Session, *, job_id: UUID) -> list[IngestionJobEvent]:
        query = (
            select(IngestionJobEvent)
            .where(IngestionJobEvent.job_id == job_id)
            .order_by(IngestionJobEvent.created_at, IngestionJobEvent.id)
        )
        return list(session.scalars(query))

    def _base_claim_query(self) -> Select[tuple[IngestionJob]]:
        return select(IngestionJob).where(IngestionJob.status == "queued").order_by(IngestionJob.requested_at, IngestionJob.id)

    def create_job(self, session: Session, payload: CreateIngestionJobInput) -> IngestionJob:
        job = IngestionJob(
            job_type=payload.job_type,
            mode=payload.mode,
            status="queued",
            requested_by=payload.requested_by,
            requested_at=datetime.now(),
            force_reprocess=payload.force_reprocess,
            source_filters=payload.source_filters,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job

    def claim_next_job(self, session: Session) -> IngestionJob | None:
        job = session.scalars(self._base_claim_query().limit(1)).first()
        if job is None:
            return None

        job.status = "running"
        job.started_at = datetime.now()
        session.commit()
        session.refresh(job)
        return job

    def add_event(
        self,
        session: Session,
        *,
        job_id: UUID,
        event_type: str,
        severity: str,
        message: str,
        event_metadata: dict | None = None,
    ) -> None:
        session.add(
            IngestionJobEvent(
                job_id=job_id,
                event_type=event_type,
                severity=severity,
                message=message,
                event_metadata=event_metadata or {},
            )
        )
        session.commit()

    def mark_job_finished(
        self,
        session: Session,
        *,
        job_id: UUID,
        status: str,
        discovered_count: int,
        downloaded_count: int,
        ingested_count: int,
        warning_count: int,
        error_count: int,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
    ) -> IngestionJob:
        job = session.get(IngestionJob, job_id)
        if job is None:
            raise ValueError(f"Ingestion job {job_id} not found")

        job.status = status
        job.finished_at = datetime.now()
        job.discovered_count = discovered_count
        job.downloaded_count = downloaded_count
        job.ingested_count = ingested_count
        job.warning_count = warning_count
        job.error_count = error_count
        job.last_error_code = last_error_code
        job.last_error_message = last_error_message
        session.commit()
        session.refresh(job)
        return job
