from app.discovery.models import DiscoveryRecord
from app.infrastructure.pdf_downloads import PdfDownloader
from app.services.ingestion import IngestionWorkflowService


class StubPdfDownloader:
    def __init__(self, payloads: dict[str, bytes]) -> None:
        self.payloads = payloads

    def download_pdf(self, source_pdf_url: str):
        from app.infrastructure.pdf_downloads import DownloadedPdf

        return DownloadedPdf(
            source_pdf_url=source_pdf_url,
            content=self.payloads[source_pdf_url],
            sha256="a" * 64,
        )


class MissingPdfDownloader:
    def download_pdf(self, source_pdf_url: str):
        raise RuntimeError("download failed")


class StubPdfParser:
    def parse_pdf_bytes(self, pdf_bytes: bytes):
        from app.parsing.transactions import ParsedDocument, ParsedTransactionRow, ParseWarning

        if pdf_bytes == b"broken":
            return ParsedDocument(
                transactions=[],
                warnings=[
                    ParseWarning(
                        code="unparsed_row",
                        message="Could not parse candidate transaction row.",
                        raw_text="1 Broken Row",
                    )
                ],
            )

        return ParsedDocument(
            transactions=[
                ParsedTransactionRow(
                    row_number=1,
                    description="Apple Inc.",
                    issuer_name="Apple Inc.",
                    trade_type="purchase",
                    trade_type_raw="Purchase",
                    transaction_date="2026-05-08",
                    transaction_date_raw="05/08/2026",
                    amount_text="$1,001 - $15,000",
                    amount_min=1001,
                    amount_max=15000,
                    raw_text="1 Apple Inc. Purchase 05/08/2026 $1,001 - $15,000",
                )
            ],
            warnings=[],
        )


class RaisingPdfParser:
    def parse_pdf_bytes(self, pdf_bytes: bytes):
        raise RuntimeError("parser crashed")


class AmbiguousDateDiscoveryClient:
    def discover_transaction_filings(self) -> list[DiscoveryRecord]:
        return [
            DiscoveryRecord(
                filing_date="07/01/26",
                position="President",
                type_label="278 Transaction",
                filer_name="Trump, Donald J",
                agency="White House Office",
                level="n/a",
                source_page_url="https://www.oge.gov/search",
                source_pdf_url="https://www.oge.gov/files/one.pdf",
            )
        ]


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


def test_workflow_downloads_and_parses_discovered_filings_into_structured_results() -> None:
    service = IngestionWorkflowService(
        discovery_client=StubDiscoveryClient(),
        pdf_downloader=StubPdfDownloader({"https://www.oge.gov/files/one.pdf": b"pdf-bytes"}),
        pdf_parser=StubPdfParser(),
    )

    result = service.ingest_discovered_filings(limit=1)

    assert result.discovered_count == 2
    assert result.skipped_missing_pdf_count == 1
    assert result.failed_count == 0
    assert len(result.filing_results) == 1
    filing_result = result.filing_results[0]
    assert filing_result.external_id.startswith("oge:")
    assert filing_result.filer_name == "Trump, Donald J"
    assert filing_result.filer_title == "President"
    assert filing_result.source_page_url == "https://www.oge.gov/search"
    assert filing_result.source_pdf_url == "https://www.oge.gov/files/one.pdf"
    assert filing_result.source_pdf_sha256 == "a" * 64
    assert len(filing_result.transactions) == 1
    assert filing_result.transactions[0].trade_type == "purchase"
    assert filing_result.transactions[0].transaction_date == "2026-05-08"
    assert filing_result.transactions[0].amount_min == 1001


def test_workflow_surfaces_download_failures_as_structured_results() -> None:
    service = IngestionWorkflowService(
        discovery_client=StubDiscoveryClient(),
        pdf_downloader=MissingPdfDownloader(),
        pdf_parser=StubPdfParser(),
    )

    result = service.ingest_discovered_filings(limit=1)

    assert result.failed_count == 1
    assert len(result.filing_results) == 1
    filing_result = result.filing_results[0]
    assert filing_result.failure is not None
    assert filing_result.failure.stage == "download"
    assert filing_result.failure.code == "download_failed"
    assert filing_result.transactions == []


def test_workflow_surfaces_parse_warnings_without_silent_drops() -> None:
    service = IngestionWorkflowService(
        discovery_client=StubDiscoveryClient(),
        pdf_downloader=StubPdfDownloader({"https://www.oge.gov/files/one.pdf": b"broken"}),
        pdf_parser=StubPdfParser(),
    )

    result = service.ingest_discovered_filings(limit=1)

    assert result.failed_count == 1
    filing_result = result.filing_results[0]
    assert filing_result.failure is not None
    assert filing_result.failure.stage == "parse"
    assert filing_result.warnings[0].code == "unparsed_row"


def test_workflow_surfaces_parser_exceptions_as_structured_failures() -> None:
    service = IngestionWorkflowService(
        discovery_client=StubDiscoveryClient(),
        pdf_downloader=StubPdfDownloader({"https://www.oge.gov/files/one.pdf": b"pdf-bytes"}),
        pdf_parser=RaisingPdfParser(),
    )

    result = service.ingest_discovered_filings(limit=1)

    assert result.failed_count == 1
    filing_result = result.filing_results[0]
    assert filing_result.failure is not None
    assert filing_result.failure.stage == "parse"
    assert filing_result.failure.code == "parse_failed"
    assert filing_result.failure.message == "parser crashed"


def test_workflow_preserves_ambiguous_filing_dates_without_normalizing() -> None:
    service = IngestionWorkflowService(
        discovery_client=AmbiguousDateDiscoveryClient(),
        pdf_downloader=StubPdfDownloader({"https://www.oge.gov/files/one.pdf": b"pdf-bytes"}),
        pdf_parser=StubPdfParser(),
    )

    result = service.ingest_discovered_filings(limit=1)

    filing_result = result.filing_results[0]
    assert filing_result.filing_date is None
    assert filing_result.filing_date_raw == "07/01/26"
    assert len(filing_result.warnings) == 1
    assert filing_result.warnings[0].code == "ambiguous_filing_date"


def test_pdf_downloader_rejects_non_canonical_source_urls_before_fetch() -> None:
    downloader = PdfDownloader()

    import pytest

    with pytest.raises(ValueError, match="Invalid source PDF URL"):
        downloader.download_pdf("https://evil.example/trump-278t.pdf")
