from __future__ import annotations

import logging
from time import sleep

from app.core.config import settings
from app.db.session import new_db_session
from app.workers.ingestion import IngestionWorkerService


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_forever() -> None:
    worker = IngestionWorkerService()

    while True:
        processed = 0
        while processed < settings.ingest_worker_max_jobs_per_run:
            session = new_db_session()
            try:
                result = worker.run_next_job(session)
            finally:
                session.close()

            if result is None:
                break

            processed += 1

        if processed == 0:
            logger.info("ingestion_worker_idle")
        sleep(settings.ingest_worker_poll_interval_seconds)


if __name__ == "__main__":
    run_forever()
