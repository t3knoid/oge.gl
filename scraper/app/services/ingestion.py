from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.discovery.models import DiscoveryRecord


class DiscoveryClient(Protocol):
    def discover_transaction_filings(self) -> list[DiscoveryRecord]: ...


@dataclass
class DiscoveryWorkflowResult:
    discovered_count: int
    eligible_records: list[DiscoveryRecord]
    skipped_missing_pdf_count: int


class IngestionWorkflowService:
    def __init__(self, discovery_client: DiscoveryClient | None = None) -> None:
        if discovery_client is None:
            from app.discovery.client import OgeDiscoveryClient

            discovery_client = OgeDiscoveryClient()

        self.discovery_client = discovery_client

    def run_incremental_discovery(self, *, limit: int | None = None) -> DiscoveryWorkflowResult:
        discovered = self.discovery_client.discover_transaction_filings()
        eligible_records = [record for record in discovered if record.source_pdf_url]
        skipped_missing_pdf_count = len(discovered) - len(eligible_records)
        if limit is not None:
            eligible_records = eligible_records[:limit]

        return DiscoveryWorkflowResult(
            discovered_count=len(discovered),
            eligible_records=eligible_records,
            skipped_missing_pdf_count=skipped_missing_pdf_count,
        )
