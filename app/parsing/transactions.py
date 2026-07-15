from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from app.core.config import settings
from app.parsing.dates import OGE_DATE_TOKEN_PATTERN, normalize_oge_date


ROW_RE = re.compile(
    rf"^\s*(\d+)\s+(.+?)\s+(purchase|sale|exchange|unsolicited|solicited|other)\b(?:\s+({OGE_DATE_TOKEN_PATTERN}))?(?:\s+(.+))?$",
    re.I,
)
CANDIDATE_ROW_RE = re.compile(r"^\s*\d+\s+")
AMOUNT_RANGE_RE = re.compile(r"^\$?([\d,\s]+)\s*-\s*\$?([\d,\s]+)$")
AMOUNT_OVER_RE = re.compile(r"^Over\s+\$?([\d,\s]+)$", re.I)
AMOUNT_RANGE_SEARCH_RE = re.compile(r"\$?\s*\d[\d,\s]*\s*-\s*\$?\s*\d[\d,\s]*")
AMOUNT_OVER_SEARCH_RE = re.compile(r"Over\s+\$?\s*\d[\d,\s]*", re.I)
CONTINUATION_HINT_RE = re.compile(
    r"(purchase|sale|exchange|unsolicited|solicited|other|\$|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}|owned|joint|spouse)",
    re.I,
)


logger = logging.getLogger(__name__)


@dataclass
class ParseWarning:
    code: str
    message: str
    raw_text: str | None = None


@dataclass
class ParsedTransactionRow:
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
class ParsedDocument:
    transactions: list[ParsedTransactionRow]
    warnings: list[ParseWarning]


def _normalize_date(date_text: str | None) -> tuple[str | None, bool]:
    return normalize_oge_date(date_text)


def _normalize_amount(amount_text: str | None) -> tuple[str | None, int | None, int | None]:
    if not amount_text:
        return None, None, None

    cleaned = amount_text.strip()
    if not cleaned:
        return None, None, None

    candidate = _extract_amount_candidate(cleaned)
    if candidate is None:
        return cleaned, None, None

    range_match = AMOUNT_RANGE_RE.match(candidate)
    if range_match:
        amount_min = _parse_amount_number(range_match.group(1))
        amount_max = _parse_amount_number(range_match.group(2))
        if amount_max < amount_min:
            return candidate, None, None
        return candidate, amount_min, amount_max

    over_match = AMOUNT_OVER_RE.match(candidate)
    if over_match:
        amount_min = _parse_amount_number(over_match.group(1))
        return candidate, amount_min, None

    return candidate, None, None


def _extract_amount_candidate(value: str) -> str | None:
    range_match = AMOUNT_RANGE_SEARCH_RE.search(value)
    if range_match is not None:
        return re.sub(r"\s+", " ", range_match.group(0)).strip()

    over_match = AMOUNT_OVER_SEARCH_RE.search(value)
    if over_match is not None:
        return re.sub(r"\s+", " ", over_match.group(0)).strip()

    return value


def _parse_amount_number(value: str) -> int:
    return int(value.replace(",", "").replace(" ", ""))


def parse_row_line(line: str) -> dict | None:
    match = ROW_RE.match(line)
    if not match:
        return None

    amount_text, amount_min, amount_max = _normalize_amount(match.group(5))
    trade_type_raw = match.group(3)
    transaction_date_raw = match.group(4)
    transaction_date, transaction_date_ambiguous = _normalize_date(transaction_date_raw)

    return {
        "num": int(match.group(1)),
        "issuer": match.group(2).strip(),
        "action": trade_type_raw.lower(),
        "trade_type": trade_type_raw.lower(),
        "trade_type_raw": trade_type_raw,
        "transaction_date": transaction_date,
        "transaction_date_raw": transaction_date_raw,
        "transaction_date_ambiguous": transaction_date_ambiguous,
        "amount_text": amount_text,
        "amount_min": amount_min,
        "amount_max": amount_max,
        "raw": line,
    }


def _iter_row_segments(text: str) -> list[list[str]]:
    row_segments: list[list[str]] = []
    current_parts: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if CANDIDATE_ROW_RE.match(line):
            if current_parts:
                row_segments.append(current_parts)
            current_parts = [stripped]
            continue

        if current_parts and _is_row_continuation(current_parts, stripped):
            current_parts.append(stripped)

    if current_parts:
        row_segments.append(current_parts)

    return row_segments


def _is_row_continuation(current_parts: list[str], stripped_line: str) -> bool:
    if not current_parts:
        return False

    current_row = " ".join(current_parts)
    if parse_row_line(current_row) is None:
        return True

    return CONTINUATION_HINT_RE.search(stripped_line) is not None


def _resolve_row_segment(parts: list[str]) -> tuple[str, dict | None]:
    candidate_parts: list[str] = []
    full_row = " ".join(parts)

    for part in parts:
        candidate_parts.append(part)
        candidate_row = " ".join(candidate_parts)
        parsed = parse_row_line(candidate_row)
        if parsed is not None:
            parsed["raw"] = full_row
            return full_row, parsed

    return parts[0], None


def parse_document_text(text: str) -> ParsedDocument:
    transactions: list[ParsedTransactionRow] = []
    warnings: list[ParseWarning] = []

    for parts in _iter_row_segments(text):
        logical_row, parsed = _resolve_row_segment(parts)
        if parsed is not None:
            transactions.append(
                ParsedTransactionRow(
                    row_number=parsed["num"],
                    description=parsed["issuer"],
                    issuer_name=parsed["issuer"],
                    trade_type=parsed["trade_type"],
                    trade_type_raw=parsed["trade_type_raw"],
                    transaction_date=parsed["transaction_date"],
                    transaction_date_raw=parsed["transaction_date_raw"],
                    amount_text=parsed["amount_text"],
                    amount_min=parsed["amount_min"],
                    amount_max=parsed["amount_max"],
                    raw_text=parsed["raw"],
                )
            )
            if parsed["transaction_date_ambiguous"]:
                warnings.append(
                    ParseWarning(
                        code="ambiguous_transaction_date",
                        message="The transaction date uses an ambiguous two-digit year and was not normalized.",
                        raw_text=parsed["raw"],
                    )
                )
            elif parsed["transaction_date_raw"] is None:
                warnings.append(
                    ParseWarning(
                        code="missing_transaction_date",
                        message="The transaction row is missing a transaction date and should be reviewed.",
                        raw_text=parsed["raw"],
                    )
                )
            continue

        warnings.append(
            ParseWarning(
                code="unparsed_row",
                message="Could not parse candidate transaction row.",
                raw_text=logical_row,
            )
        )
        if settings.log_enable_row_debug and logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "parser_row_diagnostic",
                extra={
                    "diagnostic_code": "unparsed_row",
                    "row_text": logical_row,
                },
            )

    return ParsedDocument(transactions=transactions, warnings=warnings)


def extract_rows_from_text(text: str) -> list[dict]:
    return [
        {
            "num": transaction.row_number,
            "issuer": transaction.issuer_name,
            "action": transaction.trade_type,
            "trade_type": transaction.trade_type,
            "trade_type_raw": transaction.trade_type_raw,
            "transaction_date": transaction.transaction_date,
            "transaction_date_raw": transaction.transaction_date_raw,
            "amount_text": transaction.amount_text,
            "amount_min": transaction.amount_min,
            "amount_max": transaction.amount_max,
            "raw": transaction.raw_text,
        }
        for transaction in parse_document_text(text).transactions
    ]


def parse_pdf_bytes(pdf_bytes: bytes) -> ParsedDocument:
    import pdfplumber

    transactions: list[ParsedTransactionRow] = []
    warnings: list[ParseWarning] = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            parsed = parse_document_text(text)
            transactions.extend(parsed.transactions)
            warnings.extend(parsed.warnings)
    return ParsedDocument(transactions=transactions, warnings=warnings)


def extract_rows_from_pdf_bytes(pdf_bytes: bytes) -> list[dict]:
    return [
        {
            "num": transaction.row_number,
            "issuer": transaction.issuer_name,
            "action": transaction.trade_type,
            "trade_type": transaction.trade_type,
            "trade_type_raw": transaction.trade_type_raw,
            "transaction_date": transaction.transaction_date,
            "transaction_date_raw": transaction.transaction_date_raw,
            "amount_text": transaction.amount_text,
            "amount_min": transaction.amount_min,
            "amount_max": transaction.amount_max,
            "raw": transaction.raw_text,
        }
        for transaction in parse_pdf_bytes(pdf_bytes).transactions
    ]


def extract_rows(path: str | Path) -> list[dict]:
    return extract_rows_from_pdf_bytes(Path(path).read_bytes())
