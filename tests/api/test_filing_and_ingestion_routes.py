from __future__ import annotations

from collections.abc import Generator
from datetime import date, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import ingestion as ingestion_routes
from app.api.dependencies import db_session_dependency
from app.db.base import Base
from app.db.models import Filing, IngestionJob, Transaction
from app.main import app
from app.services.ingestion_jobs import IngestionJobService


class RecordingExecutionCoordinator:
    def __init__(self) -> None:
        self.submitted_job_ids: list[str] = []

    def submit_job(self, job_id: object) -> None:
        self.submitted_job_ids.append(str(job_id))


class InlineExecutionCoordinator:
    def __init__(self, session: Session, *, terminal_status: str, error_code: str | None = None) -> None:
        self.session = session
        self.terminal_status = terminal_status
        self.error_code = error_code

    def submit_job(self, job_id: object) -> None:
        job = self.session.get(IngestionJob, job_id)
        assert job is not None
        job.status = "running"
        job.started_at = datetime(2026, 7, 9, 12, 10, 0)
        job.status = self.terminal_status
        job.finished_at = datetime(2026, 7, 9, 12, 11, 0)
        job.last_error_code = self.error_code
        job.last_error_message = "Queued ingestion job failed during worker execution." if self.error_code else None
        self.session.commit()


def _sqlite_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)()


def _make_client(session: Session) -> TestClient:
    def override_db() -> Generator[Session, None, None]:
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[db_session_dependency] = override_db
    return TestClient(app)


def test_filing_detail_endpoint_reads_persisted_filing() -> None:
    session = _sqlite_session()
    filing_id = uuid4()
    transaction_id = uuid4()
    session.add(
        Filing(
            id=filing_id,
            external_id="oge:test-filing",
            filer_name="Jane Doe",
            filer_title="Representative",
            agency="House of Representatives",
            report_type="278T",
            filing_date=date(2026, 5, 12),
            source_page_url="https://www.oge.gov/example",
            source_pdf_url="https://www.oge.gov/example.pdf",
            source_pdf_sha256="a" * 64,
            raw_metadata={},
            ingest_status="completed",
        )
    )
    session.add(
        Transaction(
            id=transaction_id,
            filing_id=filing_id,
            row_number=1,
            description="Apple Inc.",
            issuer_name="Apple Inc.",
            trade_type="purchase",
            trade_type_raw="Purchase",
            transaction_date=date(2026, 5, 8),
            transaction_date_raw="05/08/2026",
            amount_text="$1,001 - $15,000",
            amount_min=1001,
            amount_max=15000,
            raw_text="1 Apple Inc. Purchase 05/08/2026 $1,001 - $15,000",
        )
    )
    session.commit()

    client = _make_client(session)
    try:
        response = client.get(f"/api/v1/filings/{filing_id}")
    finally:
        app.dependency_overrides.clear()
        session.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(filing_id)
    assert payload["filer_name"] == "Jane Doe"
    assert payload["source_page_url"] == "https://www.oge.gov/example"
    assert payload["source_pdf_url"] == "https://www.oge.gov/example.pdf"
    assert payload["transaction_count"] == 1


def test_transaction_detail_endpoint_reads_persisted_transaction() -> None:
    session = _sqlite_session()
    filing_id = uuid4()
    transaction_id = uuid4()
    session.add(
        Filing(
            id=filing_id,
            external_id="oge:test-filing",
            filer_name="Jane Doe",
            filer_title="Representative",
            agency="House of Representatives",
            report_type="278T",
            filing_date=date(2026, 5, 12),
            source_page_url="https://www.oge.gov/example",
            source_pdf_url="https://www.oge.gov/example.pdf",
            source_pdf_sha256="a" * 64,
            raw_metadata={},
            ingest_status="completed",
        )
    )
    session.add(
        Transaction(
            id=transaction_id,
            filing_id=filing_id,
            row_number=1,
            description="Apple Inc.",
            issuer_name="Apple Inc.",
            trade_type="purchase",
            trade_type_raw="Purchase",
            transaction_date=date(2026, 5, 8),
            transaction_date_raw="05/08/2026",
            amount_text="$1,001 - $15,000",
            amount_min=1001,
            amount_max=15000,
            raw_text="1 Apple Inc. Purchase 05/08/2026 $1,001 - $15,000",
        )
    )
    session.commit()

    client = _make_client(session)
    try:
        response = client.get(f"/api/v1/transactions/{transaction_id}")
    finally:
        app.dependency_overrides.clear()
        session.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(transaction_id)
    assert payload["filing"]["id"] == str(filing_id)
    assert payload["filing"]["source_pdf_url"] == "https://www.oge.gov/example.pdf"
    assert payload["transaction"]["description"] == "Apple Inc."
    assert payload["transaction"]["raw_text"] == "1 Apple Inc. Purchase 05/08/2026 $1,001 - $15,000"


def test_transaction_detail_endpoint_returns_404_for_missing_transaction() -> None:
    session = _sqlite_session()
    client = _make_client(session)
    missing_id = uuid4()

    try:
        response = client.get(f"/api/v1/transactions/{missing_id}")
    finally:
        app.dependency_overrides.clear()
        session.close()

    assert response.status_code == 404
    assert response.json() == {"detail": "Transaction not found"}


def test_filing_detail_endpoint_returns_404_for_missing_filing() -> None:
    session = _sqlite_session()
    client = _make_client(session)
    missing_id = uuid4()

    try:
        response = client.get(f"/api/v1/filings/{missing_id}")
    finally:
        app.dependency_overrides.clear()
        session.close()

    assert response.status_code == 404
    assert response.json() == {"detail": "Filing not found"}


def test_ingestion_jobs_endpoint_lists_persisted_jobs() -> None:
    session = _sqlite_session()
    first_job_id = uuid4()
    second_job_id = uuid4()
    session.add(
        IngestionJob(
            id=first_job_id,
            job_type="incremental_ingest",
            mode="incremental",
            status="queued",
            requested_at=datetime(2026, 7, 9, 12, 0, 0),
            force_reprocess=False,
            source_filters={"type": "278 Transaction", "limit": 10},
            discovered_count=0,
            downloaded_count=0,
            ingested_count=0,
            warning_count=0,
            error_count=0,
        )
    )
    session.add(
        IngestionJob(
            id=second_job_id,
            job_type="incremental_ingest",
            mode="incremental",
            status="succeeded",
            requested_at=datetime(2026, 7, 9, 12, 5, 0),
            force_reprocess=False,
            source_filters={"type": "278 Transaction", "limit": 5},
            discovered_count=3,
            downloaded_count=0,
            ingested_count=0,
            warning_count=1,
            error_count=0,
        )
    )
    session.commit()

    client = _make_client(session)
    try:
        response = client.get("/api/v1/ingest/jobs")
    finally:
        app.dependency_overrides.clear()
        session.close()

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["items"]] == [str(second_job_id), str(first_job_id)]
    assert payload["items"][0]["status"] == "succeeded"
    assert payload["items"][0]["warning_count"] == 1
    assert payload["items"][1]["status"] == "queued"


def test_ingestion_run_endpoint_creates_queued_job() -> None:
    session = _sqlite_session()
    client = _make_client(session)

    try:
        response = client.post(
            "/api/v1/ingest/run",
            json={
                "mode": "incremental",
                "limit": 3,
                "force_reprocess": True,
                "source_filters": {"type": "278 Transaction", "agency": "House"},
            },
        )
        created_job = session.scalar(select(IngestionJob))
    finally:
        app.dependency_overrides.clear()
        session.close()

    assert response.status_code == 202
    payload = response.json()
    assert created_job is not None
    assert payload["job_id"] == str(created_job.id)
    assert payload["status"] == "queued"
    assert created_job.status == "queued"
    assert created_job.mode == "incremental"
    assert created_job.force_reprocess is True
    assert created_job.source_filters == {"type": "278 Transaction", "agency": "House"}


def test_ingestion_run_endpoint_triggers_execution_handoff(monkeypatch) -> None:
    session = _sqlite_session()
    client = _make_client(session)
    coordinator = RecordingExecutionCoordinator()
    original_service = ingestion_routes.service
    monkeypatch.setattr(ingestion_routes, "service", IngestionJobService(executor=coordinator))

    try:
        response = client.post(
            "/api/v1/ingest/run",
            json={
                "mode": "incremental",
                "limit": 2,
            },
        )
    finally:
        monkeypatch.setattr(ingestion_routes, "service", original_service)
        app.dependency_overrides.clear()
        session.close()

    assert response.status_code == 202
    payload = response.json()
    assert coordinator.submitted_job_ids == [payload["job_id"]]


def test_ingestion_run_endpoint_surfaces_succeeded_job_status_after_execution(monkeypatch) -> None:
    session = _sqlite_session()
    client = _make_client(session)
    coordinator = InlineExecutionCoordinator(session, terminal_status="succeeded")
    original_service = ingestion_routes.service
    monkeypatch.setattr(ingestion_routes, "service", IngestionJobService(executor=coordinator))

    try:
        create_response = client.post(
            "/api/v1/ingest/run",
            json={
                "mode": "incremental",
                "limit": 1,
            },
        )
        list_response = client.get("/api/v1/ingest/jobs")
    finally:
        monkeypatch.setattr(ingestion_routes, "service", original_service)
        app.dependency_overrides.clear()
        session.close()

    assert create_response.status_code == 202
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["items"][0]["status"] == "succeeded"
    assert payload["items"][0]["started_at"] is not None
    assert payload["items"][0]["finished_at"] is not None


def test_ingestion_run_endpoint_surfaces_failed_job_status_after_execution(monkeypatch) -> None:
    session = _sqlite_session()
    client = _make_client(session)
    coordinator = InlineExecutionCoordinator(
        session,
        terminal_status="failed",
        error_code="worker_execution_failed",
    )
    original_service = ingestion_routes.service
    monkeypatch.setattr(ingestion_routes, "service", IngestionJobService(executor=coordinator))

    try:
        create_response = client.post(
            "/api/v1/ingest/run",
            json={
                "mode": "incremental",
                "limit": 1,
            },
        )
        list_response = client.get("/api/v1/ingest/jobs")
        created_job = session.scalar(select(IngestionJob))
    finally:
        monkeypatch.setattr(ingestion_routes, "service", original_service)
        app.dependency_overrides.clear()
        session.close()

    assert create_response.status_code == 202
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["items"][0]["status"] == "failed"
    assert created_job is not None
    assert created_job.last_error_code == "worker_execution_failed"


def test_ingestion_run_endpoint_validates_request_body() -> None:
    session = _sqlite_session()
    client = _make_client(session)

    try:
        response = client.post(
            "/api/v1/ingest/run",
            json={
                "mode": "incremental",
                "limit": 0,
            },
        )
    finally:
        app.dependency_overrides.clear()
        session.close()

    assert response.status_code == 422
    payload = response.json()
    assert payload["detail"][0]["loc"] == ["body", "limit"]
