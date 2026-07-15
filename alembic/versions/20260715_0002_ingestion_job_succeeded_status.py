"""align ingestion job terminal statuses

Revision ID: 20260715_0002
Revises: 20260709_0001
Create Date: 2026-07-15 00:00:00
"""

from __future__ import annotations

from alembic import op


revision = "20260715_0002"
down_revision = "20260709_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE ingestion_jobs SET status = 'succeeded' WHERE status = 'completed'")
    op.execute("UPDATE ingestion_jobs SET status = 'failed' WHERE status = 'partial'")
    op.drop_constraint("ck_ingestion_jobs_status", "ingestion_jobs", type_="check")
    op.create_check_constraint(
        "ck_ingestion_jobs_status",
        "ingestion_jobs",
        "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
    )


def downgrade() -> None:
    op.execute("UPDATE ingestion_jobs SET status = 'completed' WHERE status = 'succeeded'")
    op.execute(
        """
        UPDATE ingestion_jobs
        SET status = 'partial'
        WHERE status = 'failed'
          AND ingested_count > 0
          AND (warning_count > 0 OR error_count > 0)
        """
    )
    op.drop_constraint("ck_ingestion_jobs_status", "ingestion_jobs", type_="check")
    op.create_check_constraint(
        "ck_ingestion_jobs_status",
        "ingestion_jobs",
        "status IN ('queued', 'running', 'completed', 'failed', 'cancelled', 'partial')",
    )