from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Filing, Transaction


@dataclass
class FilingDetailResult:
    filing: Filing
    transaction_count: int


class FilingRepository:
    def get_filing(self, session: Session, filing_id: UUID) -> FilingDetailResult | None:
        query = (
            select(Filing, func.count(Transaction.id))
            .outerjoin(Transaction, Transaction.filing_id == Filing.id)
            .where(Filing.id == filing_id)
            .group_by(Filing.id)
        )
        row = session.execute(query).one_or_none()
        if row is None:
            return None

        filing, transaction_count = row
        return FilingDetailResult(filing=filing, transaction_count=transaction_count)
