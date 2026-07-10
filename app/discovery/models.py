from __future__ import annotations

from dataclasses import dataclass


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
