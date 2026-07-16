from __future__ import annotations

from datetime import datetime
import re


OGE_DATE_TOKEN_PATTERN = (
    r"(?:"
    r"\d{1,2}\s*[\/\.\-]\s*\d{1,2}\s*[\/\.\-]\s*\d{2,4}"
    r"|"
    r"\d{1,2}\s*[\/\.\-]\s*\d{2}1\d{4}"
    r"|"
    r"\d{1,2}\s*[\/\.\-]\s*\d{1,2}\d{4}"
    r"|"
    r"\d{4}\s*[\/\.\-]\s*\d{1,2}\s*[\/\.\-]\s*\d{1,2}"
    r"|"
    r"\d{3,4}\s*[\/\.\-]\s*\d{4}"
    r"|"
    r"\d{4}\s*=\s*\d{1,2}"
    r"|"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t)?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2},?\s+\d{2,4}"
    r"|"
    r"\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t)?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{2,4}"
    r")"
)

AMBIGUOUS_NUMERIC_DATE_RE = re.compile(r"^\d{1,2}[\/.\-]\d{1,2}[\/.\-]\d{2}$")


def normalize_oge_date(date_text: str | None) -> tuple[str | None, bool]:
    if not date_text:
        return None, False

    cleaned = _clean_date_text(date_text)
    if not cleaned:
        return None, False

    if AMBIGUOUS_NUMERIC_DATE_RE.match(cleaned):
        return None, True

    candidates = [cleaned]
    repaired_compact_candidate = _repair_compact_month_day_year(cleaned)
    if repaired_compact_candidate is not None:
        candidates.append(repaired_compact_candidate)

    repaired_ocr_candidate = _repair_ocr_compact_month_day_year(cleaned)
    if repaired_ocr_candidate is not None:
        candidates.append(repaired_ocr_candidate)

    repaired_missing_separator_candidate = _repair_missing_day_year_separator(cleaned)
    if repaired_missing_separator_candidate is not None:
        candidates.append(repaired_missing_separator_candidate)

    repaired_artifact_separator_candidate = _repair_day_year_artifact_digit(cleaned)
    if repaired_artifact_separator_candidate is not None:
        candidates.append(repaired_artifact_separator_candidate)

    comma_stripped = cleaned.replace(",", "")
    if comma_stripped != cleaned:
        candidates.append(comma_stripped)

    formats = (
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%m.%d.%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%b %d %Y",
        "%B %d %Y",
        "%d %b %Y",
        "%d %B %Y",
    )

    for candidate in candidates:
        for fmt in formats:
            try:
                return datetime.strptime(candidate, fmt).date().isoformat(), False
            except ValueError:
                continue

    return None, False


def _clean_date_text(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    normalized = re.sub(r"\s*([\/.\-])\s*", r"\1", normalized)
    normalized = normalized.strip("()[]{}")
    normalized = normalized.rstrip(".,;:")
    return normalized


def _repair_compact_month_day_year(value: str) -> str | None:
    compact_match = re.match(r"^(\d{3,4})[\/.\-](\d{4})$", value)
    if compact_match is None:
        return None

    month_day = compact_match.group(1)
    year = compact_match.group(2)

    if len(month_day) == 3:
        month_text = month_day[0]
        day_text = month_day[1:]
        if _valid_month_day(month_text, day_text):
            return f"{month_text}/{day_text}/{year}"
        return None

    if len(month_day) == 4:
        month_text = month_day[:2]
        day_text = month_day[2:]
        if _valid_month_day(month_text, day_text):
            return f"{month_text}/{day_text}/{year}"

        # OCR can inject a separator artifact inside compact month/day tokens,
        # e.g. 2126/2026 where 2/26/2026 was expected.
        fallback_month_text = month_day[0]
        fallback_day_text = month_day[2:]
        if _valid_month_day(fallback_month_text, fallback_day_text):
            return f"{fallback_month_text}/{fallback_day_text}/{year}"

    return None


def _repair_ocr_compact_month_day_year(value: str) -> str | None:
    compact_match = re.match(r"^(\d)(\d{2})=(\d{1,2})$", value)
    if compact_match is not None:
        month_text = compact_match.group(1)
        day_text = compact_match.group(2)
        year_suffix = compact_match.group(3)
        if not _valid_month_day(month_text, day_text):
            return None

        year_text = f"202{year_suffix}" if len(year_suffix) == 1 else f"20{year_suffix}"
        return f"{month_text}/{day_text}/{year_text}"

    artifact_match = re.match(r"^(\d)\d(\d{2})=(\d{1,2})$", value)
    if artifact_match is None:
        return None

    month_text = artifact_match.group(1)
    day_text = artifact_match.group(2)
    year_suffix = artifact_match.group(3)
    if not _valid_month_day(month_text, day_text):
        return None

    year_text = f"202{year_suffix}" if len(year_suffix) == 1 else f"20{year_suffix}"
    return f"{month_text}/{day_text}/{year_text}"


def _repair_missing_day_year_separator(value: str) -> str | None:
    compact_match = re.match(r"^(\d{1,2})[\/\.\-](\d{1,2})(\d{4})$", value)
    if compact_match is None:
        return None

    month_text = compact_match.group(1)
    day_text = compact_match.group(2)
    year_text = compact_match.group(3)
    if not _valid_month_day(month_text, day_text):
        return None

    return f"{month_text}/{day_text}/{year_text}"


def _repair_day_year_artifact_digit(value: str) -> str | None:
    artifact_match = re.match(r"^(\d{1,2})[\/\.\-](\d{2})1(\d{4})$", value)
    if artifact_match is None:
        return None

    month_text = artifact_match.group(1)
    day_text = artifact_match.group(2)
    year_text = artifact_match.group(3)
    if not _valid_month_day(month_text, day_text):
        return None

    return f"{month_text}/{day_text}/{year_text}"


def _valid_month_day(month_text: str, day_text: str) -> bool:
    month = int(month_text)
    day = int(day_text)
    return 1 <= month <= 12 and 1 <= day <= 31