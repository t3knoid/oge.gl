from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import db_session_dependency
from app.schemas.transactions import TransactionDetailResponse, TransactionListResponse
from app.services.transactions import TransactionListQuery, TransactionService


router = APIRouter()
service = TransactionService()


@router.get("/transactions", response_model=TransactionListResponse)
def list_transactions(
    filer_name: str | None = Query(default=None),
    description: str | None = Query(default=None),
    trade_type: str | None = Query(default=None),
    transaction_date: date | None = Query(default=None),
    transaction_date_from: date | None = Query(default=None),
    transaction_date_to: date | None = Query(default=None),
    amount_text: str | None = Query(default=None),
    amount_min: int | None = Query(default=None),
    amount_max: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort: Literal["transaction_date", "filing_date", "filer_name", "description", "amount_min"] = Query(
        default="transaction_date"
    ),
    order: Literal["asc", "desc"] = Query(default="desc"),
    session: Session = Depends(db_session_dependency),
) -> TransactionListResponse:
    query = TransactionListQuery(
        filer_name=filer_name,
        description=description,
        trade_type=trade_type,
        transaction_date=transaction_date,
        transaction_date_from=transaction_date_from,
        transaction_date_to=transaction_date_to,
        amount_text=amount_text,
        amount_min=amount_min,
        amount_max=amount_max,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
    )
    return service.list_transactions(session, query)


@router.get("/transactions/{transaction_id}", response_model=TransactionDetailResponse)
def get_transaction(transaction_id: UUID, session: Session = Depends(db_session_dependency)) -> TransactionDetailResponse:
    transaction = service.get_transaction(session, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction

