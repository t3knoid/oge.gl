from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class IngestionRunRequest(BaseModel):
    mode: str = "incremental"
    limit: int | None = Field(default=None, ge=1)
    force_reprocess: bool = False
    source_filters: dict | None = None


class IngestionJobAcceptedResponse(BaseModel):
    job_id: str
    status: str
    accepted_at: datetime


class IngestionJobItem(BaseModel):
    id: str
    job_type: str
    status: str
    requested_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    discovered_count: int
    downloaded_count: int
    ingested_count: int
    warning_count: int
    error_count: int


class IngestionJobListResponse(BaseModel):
    items: list[IngestionJobItem]


class IngestionJobEventItem(BaseModel):
    id: str
    job_id: str
    event_type: str
    severity: str
    message: str
    event_metadata: dict
    created_at: datetime


class IngestionJobEventListResponse(BaseModel):
    items: list[IngestionJobEventItem]
