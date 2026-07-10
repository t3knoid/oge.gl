from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


DEFAULT_OGE_COLLECTION_URL = (
    "https://www.oge.gov/web/OGE.nsf/Officials%20Individual%20Disclosures%20Search%20Collection?OpenForm"
)


@dataclass
class DiscoveryRecord:
    filing_date: str
    position: str
    type_label: str
    filer_name: str
    agency: str
    level: str
    source_page_url: str
    source_pdf_url: str | None


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
        return self.parse_collection_html(self.fetch_collection_page())

    def parse_collection_html(self, html: str) -> list[DiscoveryRecord]:
        soup = BeautifulSoup(html, "html.parser")
        records: list[DiscoveryRecord] = []

        for row in soup.select("table tbody tr"):
            cells = row.find_all("td")
            if len(cells) < 6:
                continue

            filing_date = cells[0].get_text(" ", strip=True)
            position = cells[1].get_text(" ", strip=True)
            type_cell = cells[2]
            type_label = type_cell.get_text(" ", strip=True)
            if "278 Transaction" not in type_label:
                continue

            source_pdf_url = None
            link = type_cell.find("a", href=True)
            if link is not None:
                source_pdf_url = urljoin(self.base_url, link["href"])

            records.append(
                DiscoveryRecord(
                    filing_date=filing_date,
                    position=position,
                    type_label=type_label,
                    filer_name=cells[3].get_text(" ", strip=True),
                    agency=cells[4].get_text(" ", strip=True),
                    level=cells[5].get_text(" ", strip=True),
                    source_page_url=self.base_url,
                    source_pdf_url=source_pdf_url,
                )
            )

        return records
