import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, reset_request_id, sanitize_request_id, set_request_id


configure_logging(
    level=settings.log_level,
    log_format=settings.log_format,
    runtime_environment=settings.runtime_environment,
    log_file_path=settings.log_file_path,
)
logger = logging.getLogger(__name__)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    openapi_url="/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = sanitize_request_id(request.headers.get("x-request-id")) or str(uuid4())
    token = set_request_id(request_id)
    try:
        response = await call_next(request)
        if response.status_code >= 400:
            logger.warning(
                "api_request_failed",
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                },
            )
        return response
    except Exception:
        logger.exception(
            "api_request_unhandled_exception",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
            },
        )
        raise
    finally:
        reset_request_id(token)


app.include_router(api_router, prefix=settings.api_v1_prefix)
