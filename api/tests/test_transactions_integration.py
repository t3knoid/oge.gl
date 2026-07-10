from __future__ import annotations

from collections.abc import Generator
from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import db_session_dependency
from app.db.base import Base
from app.db.models import Filing, Transaction
from app.main import app


def _sqlite_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)()


def test_transactions_endpoint_reads_persisted_rows_from_sqlite() -> None:
    session = _sqlite_session()

    filing_id = uuid4()
    transaction_id = uuid4()
    filing = Filing(
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
    transaction = Transaction(
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
    session.add(filing)
    session.add(transaction)
    session.commit()

    def override_db() -> Generator[Session, None, None]:
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[db_session_dependency] = override_db
    client = TestClient(app)
    response = client.get("/api/v1/transactions")
    app.dependency_overrides.clear()
    session.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == str(transaction_id)
    assert payload["items"][0]["filer_name"] == "Jane Doe"
    assert payload["items"][0]["description"] == "Apple Inc."
