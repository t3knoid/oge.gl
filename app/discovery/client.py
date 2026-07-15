from __future__ import annotations

import html
from html.parser import HTMLParser
import json
import logging
import re
from urllib.parse import urljoin

import httpx

from app.discovery.models import DiscoveryRecord
from app.infrastructure.pdf_downloads import is_allowed_source_pdf_url


DEFAULT_OGE_COLLECTION_URL = (
    "https://www.oge.gov/web/OGE.nsf/Officials%20Individual%20Disclosures%20Search%20Collection?OpenForm"
)


logger = logging.getLogger(__name__)


class _CollectionTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_tbody = False
        self._in_row = False
        self._in_cell = False
        self._current_href: str | None = None
        self._current_cell_parts: list[str] = []
        self._current_row: list[dict[str, str | None]] = []
        self.rows: list[list[dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "tbody":
            self._in_tbody = True
            return

        if not self._in_tbody:
            return

        if tag == "tr":
            self._in_row = True
            self._current_row = []
            return

        if tag == "td" and self._in_row:
            self._in_cell = True
            self._current_href = None
            self._current_cell_parts = []
            return

        if tag == "a" and self._in_cell:
            self._current_href = attrs_dict.get("href")

    def handle_endtag(self, tag: str) -> None:
        if tag == "tbody":
            self._in_tbody = False
            return

        if tag == "td" and self._in_cell:
            text = " ".join(part for part in self._current_cell_parts if part).strip()
            self._current_row.append({"text": text, "href": self._current_href})
            self._in_cell = False
            self._current_href = None
            self._current_cell_parts = []
            return

        if tag == "tr" and self._in_row:
            self.rows.append(self._current_row)
            self._in_row = False
            self._current_row = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            stripped = data.strip()
            if stripped:
                self._current_cell_parts.append(stripped)


class OgeDiscoveryClient:
    def __init__(self, *, base_url: str = DEFAULT_OGE_COLLECTION_URL, timeout: float = 30.0) -> None:
        self.base_url = base_url
        self.timeout = timeout

    def fetch_collection_page(self) -> str:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(self.base_url)
            response.raise_for_status()
            return response.text

    def discover_transaction_filings(self) -> list[DiscoveryRecord]:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(self.base_url)
            response.raise_for_status()

            content_type = (response.headers.get("content-type") or "").lower()
            body = response.text

            if "json" in content_type:
                return self.parse_collection_json(body)

            records = self.parse_collection_html(body)
            if records:
                return records

            api_url = self._extract_json_api_url(body)
            if api_url is None:
                return records

            try:
                api_response = client.get(api_url)
                api_response.raise_for_status()
            except httpx.HTTPError:
                logger.warning(
                    "discovery_json_fallback_request_failed",
                    extra={
                        "source_page_url": self.base_url,
                        "json_api_url": api_url,
                    },
                )
                return records

            parsed_records = self.parse_collection_json(api_response.text)
            if not parsed_records:
                logger.warning(
                    "discovery_json_fallback_empty_or_invalid_payload",
                    extra={
                        "source_page_url": self.base_url,
                        "json_api_url": api_url,
                    },
                )
                return records
            return parsed_records

    def parse_collection_html(self, html: str) -> list[DiscoveryRecord]:
        parser = _CollectionTableParser()
        parser.feed(html)
        records: list[DiscoveryRecord] = []

        for cells in parser.rows:
            if len(cells) < 6:
                continue

            filing_date = (cells[0].get("text") or "").strip()
            position = (cells[1].get("text") or "").strip()
            type_cell = cells[2]
            type_label = (type_cell.get("text") or "").strip()
            if "278 Transaction" not in type_label:
                continue

            source_pdf_url = None
            href = type_cell.get("href")
            if href is not None:
                resolved_source_pdf_url = urljoin(self.base_url, href)
                if is_allowed_source_pdf_url(resolved_source_pdf_url):
                    source_pdf_url = resolved_source_pdf_url

            records.append(
                DiscoveryRecord(
                    filing_date=filing_date,
                    position=position,
                    type_label=type_label,
                    filer_name=(cells[3].get("text") or "").strip(),
                    agency=(cells[4].get("text") or "").strip(),
                    level=(cells[5].get("text") or "").strip(),
                    source_page_url=self.base_url,
                    source_pdf_url=source_pdf_url,
                )
            )

        return records

    def parse_collection_json(self, payload: str) -> list[DiscoveryRecord]:
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning("discovery_json_payload_invalid")
            return []

        items = parsed.get("data") if isinstance(parsed, dict) else None
        if not isinstance(items, list):
            return []

        records: list[DiscoveryRecord] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            type_label = str(item.get("type") or "").strip()
            if "278 Transaction" not in type_label:
                continue

            source_pdf_url = None
            decoded_type_label = html.unescape(type_label)
            href_match = re.search(r"href\s*=\s*([\"'])([^\"']+)\1", decoded_type_label, re.IGNORECASE)
            if href_match is not None:
                resolved_source_pdf_url = urljoin(self.base_url, href_match.group(2))
                if is_allowed_source_pdf_url(resolved_source_pdf_url) and self._is_direct_pdf_url(resolved_source_pdf_url):
                    source_pdf_url = resolved_source_pdf_url

            if source_pdf_url is None:
                continue

            records.append(
                DiscoveryRecord(
                    filing_date=str(item.get("date") or "").strip(),
                    position=str(item.get("title") or "").strip(),
                    type_label=type_label,
                    filer_name=str(item.get("name") or "").strip(),
                    agency=str(item.get("agency") or "").strip(),
                    level=str(item.get("level") or "").strip(),
                    source_page_url=self.base_url,
                    source_pdf_url=source_pdf_url,
                )
            )

        return records

    def _extract_json_api_url(self, page_html: str) -> str | None:
        decoded_page = html.unescape(page_html)
        match = re.search(r'"url"\s*:\s*"(https://extapps2\.oge\.gov/[^"]+/API\.xsp/v2/rest)"', decoded_page)
        if match is None:
            return None
        return match.group(1)

    def _is_direct_pdf_url(self, url: str) -> bool:
        lowered = url.lower()
        return lowered.endswith(".pdf") or "/$file/" in lowered
