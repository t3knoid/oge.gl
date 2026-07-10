from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.repositories.transactions import TransactionListFilters, TransactionRepository
from app.schemas.transactions import TransactionItem, TransactionListResponse


@dataclass
class TransactionListQuery:
    filer_name: str | None = None
    description: str | None = None
    trade_type: str | None = None
    transaction_date: date | None = None
    transaction_date_from: date | None = None
    transaction_date_to: date | None = None
    amount_text: str | None = None
    amount_min: int | None = None
    amount_max: int | None = None
    page: int = 1
    page_size: int = 50
    sort: str = "transaction_date"
    order: str = "desc"


class TransactionService:
    def __init__(self, repository: TransactionRepository | None = None) -> None:
        self.repository = repository or TransactionRepository()

    def list_transactions(self, session: Session, query: TransactionListQuery) -> TransactionListResponse:
        result = self.repository.list_transactions(
            session,
            filters=TransactionListFilters(
                filer_name=query.filer_name,
                description=query.description,
                trade_type=query.trade_type,
                transaction_date=query.transaction_date,
                transaction_date_from=query.transaction_date_from,
                transaction_date_to=query.transaction_date_to,
                amount_text=query.amount_text,
                amount_min=query.amount_min,
                amount_max=query.amount_max,
            ),
            page=query.page,
            page_size=query.page_size,
            sort=query.sort,
            order=query.order,
        )

        items = [
            TransactionItem(
                id=str(transaction.id),
                filing_id=str(filing.id),
                filer_name=filing.filer_name,
                filer_title=filing.filer_title,
                agency=filing.agency,
                description=transaction.description,
                issuer_name=transaction.issuer_name,
                trade_type=transaction.trade_type,
                trade_type_raw=transaction.trade_type_raw,
                transaction_date=transaction.transaction_date,
                transaction_date_raw=transaction.transaction_date_raw,
                amount_text=transaction.amount_text,
                amount_min=transaction.amount_min,
                amount_max=transaction.amount_max,
                filing_date=filing.filing_date,
                source_pdf_url=filing.source_pdf_url,
            )
            for transaction, filing in result.rows
        ]
        has_more = query.page * query.page_size < result.total
        return TransactionListResponse(
            items=items,
            page=query.page,
            page_size=query.page_size,
            total=result.total,
            has_more=has_more,
            sort=query.sort,
            order=query.order,
        )
