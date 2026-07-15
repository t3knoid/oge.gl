from __future__ import annotations

import logging
from time import sleep

from app.core.config import settings
from app.core.logging import configure_logging
from app.infrastructure.ingestion_execution import IngestionJobExecutionRunner
from app.workers.ingestion import IngestionWorkerService


configure_logging(
    level=settings.log_level,
    log_format=settings.log_format,
    runtime_environment=settings.runtime_environment,
    log_file_path=settings.log_file_path,
)
logger = logging.getLogger(__name__)


def run_forever() -> None:
    runner = IngestionJobExecutionRunner(worker_service_factory=IngestionWorkerService)

    while True:
        processed = runner.run_queued_jobs()

        if processed == 0:
            logger.info("ingestion_worker_idle")
        sleep(settings.ingest_worker_poll_interval_seconds)


if __name__ == "__main__":
    run_forever()
