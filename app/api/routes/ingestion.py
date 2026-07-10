from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import db_session_dependency
from app.schemas.ingestion_jobs import IngestionJobAcceptedResponse, IngestionJobListResponse, IngestionRunRequest
from app.services.ingestion_jobs import IngestionJobService, IngestionRunCommand


router = APIRouter()
service = IngestionJobService()


@router.get("/ingest/jobs", response_model=IngestionJobListResponse)
def list_ingestion_jobs(session: Session = Depends(db_session_dependency)) -> IngestionJobListResponse:
    return service.list_jobs(session)


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
