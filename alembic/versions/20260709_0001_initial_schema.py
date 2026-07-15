"""initial schema

Revision ID: 20260709_0001
Revises:
Create Date: 2026-07-09 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260709_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "filings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("filer_name", sa.Text(), nullable=False),
        sa.Column("filer_title", sa.Text(), nullable=True),
        sa.Column("agency", sa.Text(), nullable=True),
        sa.Column("report_type", sa.String(length=16), nullable=False, server_default="278T"),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.Column("report_period_start", sa.Date(), nullable=True),
        sa.Column("report_period_end", sa.Date(), nullable=True),
        sa.Column("source_page_url", sa.Text(), nullable=False),
        sa.Column("source_pdf_url", sa.Text(), nullable=False),
        sa.Column("source_pdf_sha256", sa.String(length=64), nullable=False),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("ingest_status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "ingest_status IN ('pending', 'processing', 'completed', 'partial', 'failed')",
            name="ck_filings_ingest_status",
        ),
        sa.UniqueConstraint("external_id"),
        sa.UniqueConstraint("source_pdf_sha256"),
        sa.UniqueConstraint("source_pdf_url"),
    )
    op.create_index("ix_filings_filer_name", "filings", ["filer_name"])
    op.create_index("ix_filings_filing_date", "filings", ["filing_date"])
    op.create_index("ix_filings_ingest_status", "filings", ["ingest_status"])

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("requested_by", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("force_reprocess", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source_filters", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("discovered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("downloaded_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ingested_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_ingestion_jobs_status",
        ),
    )
    op.create_index("ix_ingestion_jobs_requested_at", "ingestion_jobs", ["requested_at"])
    op.create_index("ix_ingestion_jobs_status", "ingestion_jobs", ["status"])

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("filing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("issuer_name", sa.Text(), nullable=True),
        sa.Column("trade_type", sa.String(length=32), nullable=False),
        sa.Column("trade_type_raw", sa.Text(), nullable=True),
        sa.Column("transaction_date", sa.Date(), nullable=True),
        sa.Column("transaction_date_raw", sa.Text(), nullable=True),
        sa.Column("amount_text", sa.Text(), nullable=True),
        sa.Column("amount_min", sa.Integer(), nullable=True),
        sa.Column("amount_max", sa.Integer(), nullable=True),
        sa.Column("ownership_type", sa.Text(), nullable=True),
        sa.Column("commentary", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "trade_type IN ('purchase', 'sale', 'exchange', 'unsolicited', 'solicited', 'other')",
            name="ck_transactions_trade_type",
        ),
        sa.CheckConstraint(
            "amount_min IS NULL OR amount_max IS NULL OR amount_min <= amount_max",
            name="ck_transactions_amount_bounds",
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_transactions_confidence_score",
        ),
        sa.ForeignKeyConstraint(["filing_id"], ["filings.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("filing_id", "row_number", "raw_text", name="uq_transactions_filing_row_raw"),
    )
    op.create_index("ix_transactions_transaction_date", "transactions", ["transaction_date"])
    op.create_index("ix_transactions_trade_type", "transactions", ["trade_type"])
    op.create_index("ix_transactions_amount_min", "transactions", ["amount_min"])
    op.create_index("ix_transactions_amount_max", "transactions", ["amount_max"])

    op.create_table(
        "ingestion_job_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["ingestion_jobs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ingestion_job_events_job_id_created_at", "ingestion_job_events", ["job_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_ingestion_job_events_job_id_created_at", table_name="ingestion_job_events")
    op.drop_table("ingestion_job_events")
    op.drop_index("ix_transactions_amount_max", table_name="transactions")
    op.drop_index("ix_transactions_amount_min", table_name="transactions")
    op.drop_index("ix_transactions_trade_type", table_name="transactions")
    op.drop_index("ix_transactions_transaction_date", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_ingestion_jobs_status", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_requested_at", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
    op.drop_index("ix_filings_ingest_status", table_name="filings")
    op.drop_index("ix_filings_filing_date", table_name="filings")
    op.drop_index("ix_filings_filer_name", table_name="filings")
    op.drop_table("filings")
