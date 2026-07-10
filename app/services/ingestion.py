from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Protocol

from app.discovery.models import DiscoveryRecord
from app.infrastructure.pdf_downloads import PdfDownloader
from app.parsing.transactions import ParseWarning, ParsedDocument, ParsedTransactionRow, parse_pdf_bytes


class DiscoveryClient(Protocol):
    def discover_transaction_filings(self) -> list[DiscoveryRecord]: ...


class PdfParser(Protocol):
    def parse_pdf_bytes(self, pdf_bytes: bytes) -> ParsedDocument: ...


@dataclass
class DiscoveryWorkflowResult:
    discovered_count: int
    eligible_records: list[DiscoveryRecord]
    skipped_missing_pdf_count: int


@dataclass
class WorkflowFailure:
    stage: str
    code: str
    message: str


@dataclass
class WorkflowWarning:
    code: str
    message: str
    raw_text: str | None = None


@dataclass
class NormalizedTransactionResult:
    row_number: int
    description: str
    issuer_name: str | None
    trade_type: str
    trade_type_raw: str | None
    transaction_date: str | None
    transaction_date_raw: str | None
    amount_text: str | None
    amount_min: int | None
    amount_max: int | None
    raw_text: str


@dataclass
class FilingIngestionResult:
    external_id: str
    filer_name: str
    filer_title: str | None
    agency: str | None
    filing_date: str | None
    filing_date_raw: str
    report_type: str
    source_page_url: str
    source_pdf_url: str
    source_pdf_sha256: str
    raw_metadata: dict
    transactions: list[NormalizedTransactionResult]
    warnings: list[WorkflowWarning]
    failure: WorkflowFailure | None = None


@dataclass
class IngestionWorkflowResult:
    discovered_count: int
    filing_results: list[FilingIngestionResult]
    skipped_missing_pdf_count: int
    failed_count: int


class IngestionWorkflowService:
    def __init__(
        self,
        discovery_client: DiscoveryClient | None = None,
        pdf_downloader: PdfDownloader | None = None,
        pdf_parser: PdfParser | None = None,
    ) -> None:
        if discovery_client is None:
            from app.discovery.client import OgeDiscoveryClient

            discovery_client = OgeDiscoveryClient()

        self.discovery_client = discovery_client
        self.pdf_downloader = pdf_downloader or PdfDownloader()
        self.pdf_parser = pdf_parser or _DefaultPdfParser()

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

    def ingest_discovered_filings(self, *, limit: int | None = None) -> IngestionWorkflowResult:
        discovery_result = self.run_incremental_discovery(limit=limit)
        filing_results = [self._ingest_record(record) for record in discovery_result.eligible_records]
        failed_count = sum(1 for result in filing_results if result.failure is not None)
        return IngestionWorkflowResult(
            discovered_count=discovery_result.discovered_count,
            filing_results=filing_results,
            skipped_missing_pdf_count=discovery_result.skipped_missing_pdf_count,
            failed_count=failed_count,
        )

    def build_filing_result_from_pdf_bytes(
        self,
        record: DiscoveryRecord,
        pdf_bytes: bytes,
        *,
        source_pdf_sha256: str | None = None,
    ) -> FilingIngestionResult:
        filing_date, filing_date_warnings = self._normalize_filing_date(record.filing_date)
        try:
            parsed_document = self.pdf_parser.parse_pdf_bytes(pdf_bytes)
        except Exception as exc:
            return FilingIngestionResult(
                external_id=self._build_external_id(record),
                filer_name=record.filer_name,
                filer_title=record.position,
                agency=record.agency,
                filing_date=filing_date,
                filing_date_raw=record.filing_date,
                report_type="278T",
                source_page_url=record.source_page_url,
                source_pdf_url=record.source_pdf_url or "",
                source_pdf_sha256=source_pdf_sha256 or hashlib.sha256(pdf_bytes).hexdigest(),
                raw_metadata={
                    "filing_date_raw": record.filing_date,
                    "position": record.position,
                    "type_label": record.type_label,
                    "level": record.level,
                },
                transactions=[],
                warnings=filing_date_warnings,
                failure=WorkflowFailure(stage="parse", code="parse_failed", message=str(exc)),
            )

        warnings = filing_date_warnings + [
            WorkflowWarning(code=warning.code, message=warning.message, raw_text=warning.raw_text)
            for warning in parsed_document.warnings
        ]
        transactions = [self._map_transaction(transaction) for transaction in parsed_document.transactions]
        failure = None
        if not transactions:
            failure = WorkflowFailure(
                stage="parse",
                code="parse_failed",
                message="The PDF did not yield any parsed transaction rows.",
            )

        return FilingIngestionResult(
            external_id=self._build_external_id(record),
            filer_name=record.filer_name,
            filer_title=record.position,
            agency=record.agency,
            filing_date=filing_date,
            filing_date_raw=record.filing_date,
            report_type="278T",
            source_page_url=record.source_page_url,
            source_pdf_url=record.source_pdf_url or "",
            source_pdf_sha256=source_pdf_sha256 or hashlib.sha256(pdf_bytes).hexdigest(),
            raw_metadata={
                "filing_date_raw": record.filing_date,
                "position": record.position,
                "type_label": record.type_label,
                "level": record.level,
            },
            transactions=transactions,
            warnings=warnings,
            failure=failure,
        )

    def _ingest_record(self, record: DiscoveryRecord) -> FilingIngestionResult:
        source_pdf_url = record.source_pdf_url
        filing_date, filing_date_warnings = self._normalize_filing_date(record.filing_date)
        if not source_pdf_url:
            return FilingIngestionResult(
                external_id=self._build_external_id(record),
                filer_name=record.filer_name,
                filer_title=record.position,
                agency=record.agency,
                filing_date=filing_date,
                filing_date_raw=record.filing_date,
                report_type="278T",
                source_page_url=record.source_page_url,
                source_pdf_url="",
                source_pdf_sha256="",
                raw_metadata={"type_label": record.type_label, "level": record.level},
                transactions=[],
                warnings=filing_date_warnings,
                failure=WorkflowFailure(
                    stage="discovery",
                    code="missing_source_pdf_url",
                    message="The discovery record does not contain a source PDF URL.",
                ),
            )

        try:
            downloaded_pdf = self.pdf_downloader.download_pdf(source_pdf_url)
        except Exception as exc:
            return FilingIngestionResult(
                external_id=self._build_external_id(record),
                filer_name=record.filer_name,
                filer_title=record.position,
                agency=record.agency,
                filing_date=filing_date,
                filing_date_raw=record.filing_date,
                report_type="278T",
                source_page_url=record.source_page_url,
                source_pdf_url=source_pdf_url,
                source_pdf_sha256="",
                raw_metadata={"type_label": record.type_label, "level": record.level},
                transactions=[],
                warnings=filing_date_warnings,
                failure=WorkflowFailure(stage="download", code="download_failed", message=str(exc)),
            )

        return self.build_filing_result_from_pdf_bytes(
            record,
            downloaded_pdf.content,
            source_pdf_sha256=downloaded_pdf.sha256,
        )

    def _build_external_id(self, record: DiscoveryRecord) -> str:
        source_value = record.source_pdf_url or record.source_page_url
        digest = hashlib.sha256(source_value.encode("utf-8")).hexdigest()[:16]
        return f"oge:{digest}"

    def _map_transaction(self, transaction: ParsedTransactionRow) -> NormalizedTransactionResult:
        return NormalizedTransactionResult(
            row_number=transaction.row_number,
            description=transaction.description,
            issuer_name=transaction.issuer_name,
            trade_type=transaction.trade_type,
            trade_type_raw=transaction.trade_type_raw,
            transaction_date=transaction.transaction_date,
            transaction_date_raw=transaction.transaction_date_raw,
            amount_text=transaction.amount_text,
            amount_min=transaction.amount_min,
            amount_max=transaction.amount_max,
            raw_text=transaction.raw_text,
        )

    def _normalize_filing_date(self, filing_date: str) -> tuple[str | None, list[WorkflowWarning]]:
        from datetime import datetime

        if re.match(r"^\d{1,2}/\d{1,2}/\d{2}$", filing_date):
            return None, [
                WorkflowWarning(
                    code="ambiguous_filing_date",
                    message="The filing date uses an ambiguous two-digit year and was not normalized.",
                    raw_text=filing_date,
                )
            ]

        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(filing_date, fmt).date().isoformat(), []
            except ValueError:
                continue
        return None, []


class _DefaultPdfParser:
    def parse_pdf_bytes(self, pdf_bytes: bytes) -> ParsedDocument:
        return parse_pdf_bytes(pdf_bytes)
