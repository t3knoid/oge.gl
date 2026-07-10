from datetime import date
from uuid import uuid4

from app.db.models import Filing, Transaction
from app.repositories.transactions import TransactionListResult
from app.services.transactions import TransactionListQuery, TransactionService


class StubRepository:
    def list_transactions(self, session, **kwargs):  # noqa: ANN001
        filing = Filing(
            id=uuid4(),
            external_id="oge:sample",
            filer_name="Jane Doe",
            filer_title="Representative",
            agency="House",
            report_type="278T",
            filing_date=date(2026, 5, 12),
            source_page_url="https://www.oge.gov/example",
            source_pdf_url="https://www.oge.gov/example.pdf",
            source_pdf_sha256="a" * 64,
            raw_metadata={},
            ingest_status="completed",
        )
        transaction = Transaction(
            id=uuid4(),
            filing_id=filing.id,
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
            raw_text="raw row",
        )
        return TransactionListResult(rows=[(transaction, filing)], total=1)


def test_transaction_service_returns_documented_contract_shape() -> None:
    service = TransactionService(repository=StubRepository())

    result = service.list_transactions(session=None, query=TransactionListQuery())

    assert result.total == 1
    assert result.page == 1
    assert result.page_size == 50
    assert result.has_more is False
    assert result.items[0].filer_name == "Jane Doe"
    assert result.items[0].description == "Apple Inc."
