from __future__ import annotations

import logging
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import new_db_session
from app.workers.ingestion import IngestionWorkerService


logger = logging.getLogger(__name__)


class IngestionJobExecutionRunner:
    def __init__(
        self,
        *,
        session_factory: Callable[[], Session] = new_db_session,
        worker_service_factory: Callable[[], IngestionWorkerService] = IngestionWorkerService,
        max_jobs_per_run: int = settings.ingest_worker_max_jobs_per_run,
    ) -> None:
        self.session_factory = session_factory
        self.worker_service_factory = worker_service_factory
        self.max_jobs_per_run = max_jobs_per_run

    def run_queued_jobs(self) -> int:
        worker = self.worker_service_factory()
        processed = 0

        while processed < self.max_jobs_per_run:
            session = self.session_factory()
            try:
                result = worker.run_next_job(session)
            finally:
                session.close()

            if result is None:
                break

            processed += 1

        return processed


class IngestionJobExecutionCoordinator:
    def __init__(
        self,
        *,
        runner: IngestionJobExecutionRunner | None = None,
        executor: Executor | None = None,
    ) -> None:
        self.runner = runner or IngestionJobExecutionRunner()
        self.executor = executor or ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingestion-job")

    def submit_job(self, job_id: UUID) -> Future[int]:
        future = self.executor.submit(self.runner.run_queued_jobs)
        future.add_done_callback(lambda completed: self._log_completion(job_id, completed))
        return future

    def _log_completion(self, job_id: UUID, future: Future[int]) -> None:
        try:
            processed = future.result()
        except Exception:
            logger.exception("ingestion_job_dispatch_failed", extra={"job_id": str(job_id)})
            return

        logger.info(
            "ingestion_job_dispatch_complete",
            extra={
                "job_id": str(job_id),
                "processed_jobs": processed,
            },
        )