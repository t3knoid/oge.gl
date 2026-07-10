from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class TransactionItem(BaseModel):
    id: str
    filing_id: str
    filer_name: str
    filer_title: str | None = None
    agency: str | None = None
    description: str
    issuer_name: str | None = None
    trade_type: str
    trade_type_raw: str | None = None
    transaction_date: date | None = None
    transaction_date_raw: str | None = None
    amount_text: str | None = None
    amount_min: int | None = None
    amount_max: int | None = None
    filing_date: date | None = None
    source_pdf_url: str


class TransactionListResponse(BaseModel):
    items: list[TransactionItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    has_more: bool
    sort: str
    order: str
