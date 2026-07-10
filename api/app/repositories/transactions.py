from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import Filing, Transaction


@dataclass
class TransactionListFilters:
    filer_name: str | None = None
    description: str | None = None
    trade_type: str | None = None
    transaction_date: date | None = None
    transaction_date_from: date | None = None
    transaction_date_to: date | None = None
    amount_text: str | None = None
    amount_min: int | None = None
    amount_max: int | None = None


@dataclass
class TransactionListResult:
    rows: list[tuple[Transaction, Filing]]
    total: int


class TransactionRepository:
    SORT_FIELDS = {
        "transaction_date": Transaction.transaction_date,
        "filing_date": Filing.filing_date,
        "filer_name": Filing.filer_name,
        "description": Transaction.description,
        "amount_min": Transaction.amount_min,
    }

    def list_transactions(
        self,
        session: Session,
        *,
        filters: TransactionListFilters,
        page: int,
        page_size: int,
        sort: str,
        order: str,
    ) -> TransactionListResult:
        base_query = select(Transaction, Filing).join(Filing, Transaction.filing_id == Filing.id)
        filtered_query = self._apply_filters(base_query, filters)

        total = session.scalar(select(func.count()).select_from(filtered_query.subquery())) or 0
        sort_column = self.SORT_FIELDS.get(sort, Transaction.transaction_date)
        sort_expr = sort_column.asc() if order == "asc" else sort_column.desc()

        rows = session.execute(
            filtered_query.order_by(sort_expr, Transaction.id).offset((page - 1) * page_size).limit(page_size)
        ).all()
        return TransactionListResult(rows=rows, total=total)

    def get_transaction(self, session: Session, transaction_id: str) -> tuple[Transaction, Filing] | None:
        query = select(Transaction, Filing).join(Filing, Transaction.filing_id == Filing.id).where(Transaction.id == transaction_id)
        return session.execute(query).one_or_none()

    def _apply_filters(self, query: Select, filters: TransactionListFilters) -> Select:
        if filters.filer_name:
            query = query.where(Filing.filer_name.ilike(f"%{filters.filer_name}%"))
        if filters.description:
            query = query.where(
                or_(
                    Transaction.description.ilike(f"%{filters.description}%"),
                    Transaction.issuer_name.ilike(f"%{filters.description}%"),
                )
            )
        if filters.trade_type:
            query = query.where(Transaction.trade_type == filters.trade_type)
        if filters.transaction_date:
            query = query.where(Transaction.transaction_date == filters.transaction_date)
        if filters.transaction_date_from:
            query = query.where(Transaction.transaction_date >= filters.transaction_date_from)
        if filters.transaction_date_to:
            query = query.where(Transaction.transaction_date <= filters.transaction_date_to)
        if filters.amount_text:
            query = query.where(Transaction.amount_text.ilike(f"%{filters.amount_text}%"))
        if filters.amount_min is not None:
            query = query.where(or_(Transaction.amount_max.is_(None), Transaction.amount_max >= filters.amount_min))
        if filters.amount_max is not None:
            query = query.where(or_(Transaction.amount_min.is_(None), Transaction.amount_min <= filters.amount_max))
        return query
