from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import db_session_dependency
from app.schemas.filings import FilingDetailResponse
from app.services.filings import FilingService


router = APIRouter()
service = FilingService()


@router.get("/filings/{filing_id}", response_model=FilingDetailResponse)
def get_filing(filing_id: UUID, session: Session = Depends(db_session_dependency)) -> FilingDetailResponse:
    filing = service.get_filing(session, filing_id)
    if filing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filing not found")
    return filing
