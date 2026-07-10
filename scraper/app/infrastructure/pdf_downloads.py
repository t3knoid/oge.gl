from __future__ import annotations

import hashlib
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


DEFAULT_ALLOWED_SOURCE_HOSTS = frozenset({"oge.gov", "www.oge.gov"})


def is_allowed_source_pdf_url(
    source_pdf_url: str,
    *,
    allowed_hosts: frozenset[str] | None = None,
) -> bool:
    parsed = urlparse(source_pdf_url)
    if parsed.scheme not in {"http", "https"}:
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    host = hostname.lower()
    allowed = allowed_hosts or DEFAULT_ALLOWED_SOURCE_HOSTS
    return host in allowed or host.endswith(".oge.gov")


@dataclass
class DownloadedPdf:
    source_pdf_url: str
    content: bytes
    sha256: str


class PdfDownloader:
    def __init__(
        self,
        *,
        timeout: float = 30.0,
        allowed_hosts: frozenset[str] | None = None,
    ) -> None:
        self.timeout = timeout
        self.allowed_hosts = allowed_hosts or DEFAULT_ALLOWED_SOURCE_HOSTS

    def download_pdf(self, source_pdf_url: str) -> DownloadedPdf:
        if not is_allowed_source_pdf_url(source_pdf_url, allowed_hosts=self.allowed_hosts):
            raise ValueError("Invalid source PDF URL")

        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(source_pdf_url)
            response.raise_for_status()
            content = response.content

        return DownloadedPdf(
            source_pdf_url=source_pdf_url,
            content=content,
            sha256=hashlib.sha256(content).hexdigest(),
        )
