from app.discovery.models import DiscoveryRecord
from app.services.ingestion import IngestionWorkflowService


class StubDiscoveryClient:
    def discover_transaction_filings(self) -> list[DiscoveryRecord]:
        return [
            DiscoveryRecord(
                filing_date="07/01/2026",
                position="President",
                type_label="278 Transaction",
                filer_name="Trump, Donald J",
                agency="White House Office",
                level="n/a",
                source_page_url="https://www.oge.gov/search",
                source_pdf_url="https://www.oge.gov/files/one.pdf",
            ),
            DiscoveryRecord(
                filing_date="07/01/2026",
                position="Commissioner",
                type_label="278 Transaction (Request this Document)",
                filer_name="Weaver, Douglas",
                agency="Nuclear Regulatory Commission",
                level="n/a",
                source_page_url="https://www.oge.gov/search",
                source_pdf_url=None,
            ),
        ]


def test_workflow_wraps_discovery_client_and_filters_missing_pdf_records() -> None:
    service = IngestionWorkflowService(discovery_client=StubDiscoveryClient())

    result = service.run_incremental_discovery()

    assert result.discovered_count == 2
    assert result.skipped_missing_pdf_count == 1
    assert len(result.eligible_records) == 1
    assert result.eligible_records[0].source_pdf_url == "https://www.oge.gov/files/one.pdf"
