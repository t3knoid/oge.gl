from fastapi import APIRouter

from app.api.routes.filings import router as filings_router
from app.api.routes.health import router as health_router
from app.api.routes.ingestion import router as ingestion_router
from app.api.routes.transactions import router as transactions_router


api_router = APIRouter()
api_router.include_router(filings_router, tags=["filings"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(ingestion_router, tags=["ingestion"])
api_router.include_router(transactions_router, tags=["transactions"])
