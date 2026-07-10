from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Filing(Base):
    __tablename__ = "filings"
    __table_args__ = (
        CheckConstraint(
            "ingest_status IN ('pending', 'processing', 'completed', 'partial', 'failed')",
            name="ck_filings_ingest_status",
        ),
        Index("ix_filings_filing_date", "filing_date"),
        Index("ix_filings_filer_name", "filer_name"),
        Index("ix_filings_ingest_status", "ingest_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str | None] = mapped_column(Text, unique=True)
    filer_name: Mapped[str] = mapped_column(Text, nullable=False)
    filer_title: Mapped[str | None] = mapped_column(Text)
    agency: Mapped[str | None] = mapped_column(Text)
    report_type: Mapped[str] = mapped_column(String(16), nullable=False, default="278T")
    filing_date: Mapped[date | None] = mapped_column(Date)
    report_period_start: Mapped[date | None] = mapped_column(Date)
    report_period_end: Mapped[date | None] = mapped_column(Date)
    source_page_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_pdf_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source_pdf_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ingest_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    transactions: Mapped[list[Transaction]] = relationship(back_populates="filing", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("filing_id", "row_number", "raw_text", name="uq_transactions_filing_row_raw"),
        CheckConstraint(
            "trade_type IN ('purchase', 'sale', 'exchange', 'unsolicited', 'solicited', 'other')",
            name="ck_transactions_trade_type",
        ),
        CheckConstraint(
            "amount_min IS NULL OR amount_max IS NULL OR amount_min <= amount_max",
            name="ck_transactions_amount_bounds",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_transactions_confidence_score",
        ),
        Index("ix_transactions_transaction_date", "transaction_date"),
        Index("ix_transactions_trade_type", "trade_type"),
        Index("ix_transactions_amount_min", "amount_min"),
        Index("ix_transactions_amount_max", "amount_max"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("filings.id", ondelete="CASCADE"), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    issuer_name: Mapped[str | None] = mapped_column(Text)
    trade_type: Mapped[str] = mapped_column(String(32), nullable=False)
    trade_type_raw: Mapped[str | None] = mapped_column(Text)
    transaction_date: Mapped[date | None] = mapped_column(Date)
    transaction_date_raw: Mapped[str | None] = mapped_column(Text)
    amount_text: Mapped[str | None] = mapped_column(Text)
    amount_min: Mapped[int | None] = mapped_column()
    amount_max: Mapped[int | None] = mapped_column()
    ownership_type: Mapped[str | None] = mapped_column(Text)
    commentary: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(4, 3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    filing: Mapped[Filing] = relationship(back_populates="transactions")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled', 'partial')",
            name="ck_ingestion_jobs_status",
        ),
        Index("ix_ingestion_jobs_requested_at", "requested_at"),
        Index("ix_ingestion_jobs_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_by: Mapped[str | None] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    force_reprocess: Mapped[bool] = mapped_column(nullable=False, default=False)
    source_filters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    discovered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    downloaded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ingested_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    last_error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    events: Mapped[list[IngestionJobEvent]] = relationship(back_populates="job", cascade="all, delete-orphan")


class IngestionJobEvent(Base):
    __tablename__ = "ingestion_job_events"
    __table_args__ = (Index("ix_ingestion_job_events_job_id_created_at", "job_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_jobs.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    job: Mapped[IngestionJob] = relationship(back_populates="events")
