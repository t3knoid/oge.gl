from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Filing, Transaction


@dataclass
class FilingUpsertInput:
    external_id: str
    filer_name: str
    filer_title: str | None
    agency: str | None
    report_type: str
    filing_date: date | None
    source_page_url: str
    source_pdf_url: str
    source_pdf_sha256: str
    raw_metadata: dict
    ingest_status: str
    downloaded_at: datetime | None
    scraped_at: datetime | None


@dataclass
class TransactionUpsertInput:
    row_number: int
    description: str
    issuer_name: str | None
    trade_type: str
    trade_type_raw: str | None
    transaction_date: date | None
    transaction_date_raw: str | None
    amount_text: str | None
    amount_min: int | None
    amount_max: int | None
    raw_text: str


class IngestionResultRepository:
    def find_filing_by_identity(
        self,
        session: Session,
        *,
        external_id: str,
        source_pdf_url: str,
        source_pdf_sha256: str,
    ) -> Filing | None:
        predicates = [Filing.external_id == external_id]
        if source_pdf_url:
            predicates.append(Filing.source_pdf_url == source_pdf_url)
        if source_pdf_sha256:
            predicates.append(Filing.source_pdf_sha256 == source_pdf_sha256)

        return session.scalar(select(Filing).where(or_(*predicates)).limit(1))

    def count_transactions_for_filing(self, session: Session, filing_id: UUID) -> int:
        return session.scalar(select(func.count()).select_from(Transaction).where(Transaction.filing_id == filing_id)) or 0

    def upsert_filing(
        self,
        session: Session,
        *,
        existing_filing: Filing | None,
        payload: FilingUpsertInput,
    ) -> Filing:
        filing = existing_filing
        if filing is None:
            filing = Filing(
                external_id=payload.external_id,
                filer_name=payload.filer_name,
                filer_title=payload.filer_title,
                agency=payload.agency,
                report_type=payload.report_type,
                filing_date=payload.filing_date,
                source_page_url=payload.source_page_url,
                source_pdf_url=payload.source_pdf_url,
                source_pdf_sha256=payload.source_pdf_sha256,
                raw_metadata=payload.raw_metadata,
                ingest_status=payload.ingest_status,
                downloaded_at=payload.downloaded_at,
                scraped_at=payload.scraped_at,
            )
            session.add(filing)
            try:
                session.flush()
            except IntegrityError:
                session.rollback()
                filing = self.find_filing_by_identity(
                    session,
                    external_id=payload.external_id,
                    source_pdf_url=payload.source_pdf_url,
                    source_pdf_sha256=payload.source_pdf_sha256,
                )
                if filing is None:
                    raise
                self._apply_filing_updates(filing, payload)
                session.flush()
            return filing

        self._apply_filing_updates(filing, payload)
        session.flush()
        return filing

    def _apply_filing_updates(self, filing: Filing, payload: FilingUpsertInput) -> None:
        filing.external_id = payload.external_id
        filing.filer_name = payload.filer_name
        filing.filer_title = payload.filer_title
        filing.agency = payload.agency
        filing.report_type = payload.report_type
        filing.filing_date = payload.filing_date
        filing.source_page_url = payload.source_page_url
        filing.source_pdf_url = payload.source_pdf_url
        filing.source_pdf_sha256 = payload.source_pdf_sha256
        filing.raw_metadata = {**(filing.raw_metadata or {}), **payload.raw_metadata}
        filing.ingest_status = payload.ingest_status
        filing.downloaded_at = payload.downloaded_at
        filing.scraped_at = payload.scraped_at

    def replace_transactions(
        self,
        session: Session,
        *,
        filing_id: UUID,
        transactions: list[TransactionUpsertInput],
    ) -> None:
        existing_transactions = list(session.scalars(select(Transaction).where(Transaction.filing_id == filing_id)))
        existing_by_key = {(transaction.row_number, transaction.raw_text): transaction for transaction in existing_transactions}
        incoming_keys: set[tuple[int, str]] = set()

        for transaction_input in transactions:
            key = (transaction_input.row_number, transaction_input.raw_text)
            incoming_keys.add(key)
            transaction = existing_by_key.get(key)
            if transaction is None:
                session.add(
                    Transaction(
                        filing_id=filing_id,
                        row_number=transaction_input.row_number,
                        description=transaction_input.description,
                        issuer_name=transaction_input.issuer_name,
                        trade_type=transaction_input.trade_type,
                        trade_type_raw=transaction_input.trade_type_raw,
                        transaction_date=transaction_input.transaction_date,
                        transaction_date_raw=transaction_input.transaction_date_raw,
                        amount_text=transaction_input.amount_text,
                        amount_min=transaction_input.amount_min,
                        amount_max=transaction_input.amount_max,
                        raw_text=transaction_input.raw_text,
                    )
                )
                continue

            transaction.description = transaction_input.description
            transaction.issuer_name = transaction_input.issuer_name
            transaction.trade_type = transaction_input.trade_type
            transaction.trade_type_raw = transaction_input.trade_type_raw
            transaction.transaction_date = transaction_input.transaction_date
            transaction.transaction_date_raw = transaction_input.transaction_date_raw
            transaction.amount_text = transaction_input.amount_text
            transaction.amount_min = transaction_input.amount_min
            transaction.amount_max = transaction_input.amount_max

        for existing_key, existing_transaction in existing_by_key.items():
            if existing_key not in incoming_keys:
                session.delete(existing_transaction)

        session.flush()