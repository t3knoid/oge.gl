from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import db_session_dependency
from app.schemas.ingestion_jobs import (
    IngestionJobAcceptedResponse,
    IngestionJobEventListResponse,
    IngestionJobListResponse,
    IngestionRunRequest,
)
from app.services.ingestion_jobs import IngestionJobService, IngestionRunCommand


router = APIRouter()
service = IngestionJobService()


@router.get("/ingest/jobs", response_model=IngestionJobListResponse)
def list_ingestion_jobs(session: Session = Depends(db_session_dependency)) -> IngestionJobListResponse:
    return service.list_jobs(session)


@router.get("/ingest/jobs/{job_id}/events", response_model=IngestionJobEventListResponse)
def list_ingestion_job_events(
    job_id: UUID,
    session: Session = Depends(db_session_dependency),
) -> IngestionJobEventListResponse:
    response = service.list_job_events(session, job_id)
    if response is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion job not found")
    return response


@router.post("/ingest/run", response_model=IngestionJobAcceptedResponse, status_code=202)
def create_ingestion_job(
    request: IngestionRunRequest,
    session: Session = Depends(db_session_dependency),
) -> IngestionJobAcceptedResponse:
    return service.create_job(
        session,
        IngestionRunCommand(
            mode=request.mode,
            limit=request.limit,
            force_reprocess=request.force_reprocess,
            source_filters=request.source_filters,
        ),
    )
