from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="api",
        version=settings.app_version,
        time=datetime.now(UTC),
    )
