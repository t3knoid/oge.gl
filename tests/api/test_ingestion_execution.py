from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass
from uuid import uuid4

from app.infrastructure.ingestion_execution import IngestionJobExecutionCoordinator, IngestionJobExecutionRunner
from app.workers.ingestion import WorkerRunResult


@dataclass
class _FakeSession:
    closed: bool = False

    def close(self) -> None:
        self.closed = True


class _StubWorkerService:
    def __init__(self, results: list[WorkerRunResult | None]) -> None:
        self._results = results
        self.sessions: list[_FakeSession] = []

    def run_next_job(self, session: _FakeSession) -> WorkerRunResult | None:
        self.sessions.append(session)
        return self._results.pop(0)


class _InlineExecutor:
    def __init__(self) -> None:
        self.submissions = 0

    def submit(self, fn):
        self.submissions += 1
        future = Future()
        try:
            future.set_result(fn())
        except Exception as exc:  # pragma: no cover - defensive parity with Future API
            future.set_exception(exc)
        return future


def test_execution_runner_processes_jobs_until_queue_is_empty() -> None:
    worker = _StubWorkerService(
        results=[
            WorkerRunResult(
                job_id=uuid4(),
                status="succeeded",
                discovered_count=1,
                downloaded_count=1,
                ingested_count=1,
                warning_count=0,
                error_count=0,
            ),
            WorkerRunResult(
                job_id=uuid4(),
                status="failed",
                discovered_count=1,
                downloaded_count=1,
                ingested_count=0,
                warning_count=1,
                error_count=1,
            ),
            None,
        ]
    )
    sessions: list[_FakeSession] = []

    def session_factory() -> _FakeSession:
        session = _FakeSession()
        sessions.append(session)
        return session

    runner = IngestionJobExecutionRunner(
        session_factory=session_factory,
        worker_service_factory=lambda: worker,
        max_jobs_per_run=5,
    )

    processed = runner.run_queued_jobs()

    assert processed == 2
    assert len(worker.sessions) == 3
    assert all(session.closed for session in sessions)


def test_execution_coordinator_submits_runner_work() -> None:
    class _Runner:
        def __init__(self) -> None:
            self.calls = 0

        def run_queued_jobs(self) -> int:
            self.calls += 1
            return 1

    runner = _Runner()
    executor = _InlineExecutor()
    coordinator = IngestionJobExecutionCoordinator(runner=runner, executor=executor)

    coordinator.submit_job(uuid4())

    assert runner.calls == 1
    assert executor.submissions == 1