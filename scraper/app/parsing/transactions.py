from __future__ import annotations

import re
from pathlib import Path


ROW_RE = re.compile(r"^\s*(\d+)\s+(.+?)\s+(purchase|sale|exchange|unsolicited|solicited)\b", re.I)


def parse_row_line(line: str) -> dict | None:
    match = ROW_RE.match(line)
    if not match:
        return None

    return {
        "num": int(match.group(1)),
        "issuer": match.group(2).strip(),
        "action": match.group(3).lower(),
        "raw": line,
    }


def extract_rows_from_text(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        parsed = parse_row_line(line)
        if parsed:
            rows.append(parsed)
    return rows


def extract_rows(path: str | Path) -> list[dict]:
    import pdfplumber

    rows: list[dict] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            rows.extend(extract_rows_from_text(text))
    return rows
