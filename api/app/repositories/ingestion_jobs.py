from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import IngestionJob


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
