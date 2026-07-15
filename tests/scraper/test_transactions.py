import logging

from app.core.config import settings
from app.parsing.transactions import extract_rows_from_text, parse_document_text, parse_row_line


def test_parse_row_line_extracts_transaction_fields() -> None:
    row = parse_row_line("1 Apple Inc. purchase 05/08/2026 $1,001 - $15,000")

    assert row is not None
    assert row["num"] == 1
    assert row["issuer"] == "Apple Inc."
    assert row["action"] == "purchase"
    assert row["transaction_date"] == "2026-05-08"
    assert row["transaction_date_raw"] == "05/08/2026"
    assert row["amount_text"] == "$1,001 - $15,000"
    assert row["amount_min"] == 1001
    assert row["amount_max"] == 15000


def test_parse_row_line_normalizes_month_name_transaction_date() -> None:
    row = parse_row_line("1 Apple Inc. purchase May 8, 2026 $1,001 - $15,000")

    assert row is not None
    assert row["transaction_date"] == "2026-05-08"
    assert row["transaction_date_raw"] == "May 8, 2026"


def test_parse_row_line_normalizes_dashed_transaction_date_with_spacing() -> None:
    row = parse_row_line("1 Apple Inc. purchase 05 - 08 - 2026 $1,001 - $15,000")

    assert row is not None
    assert row["transaction_date"] == "2026-05-08"
    assert row["transaction_date_raw"] == "05 - 08 - 2026"


def test_parse_row_line_recovers_ocr_compact_date_and_noisy_amount_prefix() -> None:
    row = parse_row_line(
        "3075 GRIO OYNAMICS HLDGS INC CLASS A purchase 2126/2026 Yos $15 001 -$50,000"
    )

    assert row is not None
    assert row["num"] == 3075
    assert row["transaction_date"] == "2026-02-26"
    assert row["transaction_date_raw"] == "2126/2026"
    assert row["amount_text"] == "$15 001 -$50,000"
    assert row["amount_min"] == 15001
    assert row["amount_max"] == 50000


def test_parse_row_line_drops_numeric_bounds_for_inverted_ocr_amount_range() -> None:
    row = parse_row_line("2735 AMERICAN TOWER CORP NEW REIT sale 3/2812026 Vos $1,001-$15")

    assert row is not None
    assert row["amount_text"] == "$1,001-$15"
    assert row["amount_min"] is None
    assert row["amount_max"] is None


def test_extract_rows_from_text_ignores_non_transaction_lines() -> None:
    text = "Header line\n1 Apple Inc. purchase\nFooter line\n2 Microsoft sale"

    rows = extract_rows_from_text(text)

    assert [row["num"] for row in rows] == [1, 2]
    assert rows[0]["raw"] == "1 Apple Inc. purchase"


def test_parse_document_text_surfaces_candidate_row_failures() -> None:
    parsed = parse_document_text("Header\n1 Unparseable Candidate Row\nFooter")

    assert parsed.transactions == []
    assert len(parsed.warnings) == 1
    assert parsed.warnings[0].code == "unparsed_row"
    assert parsed.warnings[0].raw_text == "1 Unparseable Candidate Row"


def test_parse_document_text_preserves_ambiguous_two_digit_years_as_raw_only() -> None:
    parsed = parse_document_text("1 Apple Inc. purchase 05/08/26 $1,001 - $15,000")

    assert len(parsed.transactions) == 1
    assert parsed.transactions[0].transaction_date is None
    assert parsed.transactions[0].transaction_date_raw == "05/08/26"
    assert len(parsed.warnings) == 1
    assert parsed.warnings[0].code == "ambiguous_transaction_date"


def test_parse_document_text_flags_ambiguous_two_digit_year_with_dash_separator() -> None:
    parsed = parse_document_text("1 Apple Inc. purchase 05-08-26 $1,001 - $15,000")

    assert len(parsed.transactions) == 1
    assert parsed.transactions[0].transaction_date is None
    assert parsed.transactions[0].transaction_date_raw == "05-08-26"
    assert len(parsed.warnings) == 1
    assert parsed.warnings[0].code == "ambiguous_transaction_date"


def test_parse_document_text_flags_missing_transaction_dates() -> None:
    parsed = parse_document_text("1 Apple Inc. purchase")

    assert len(parsed.transactions) == 1
    assert parsed.transactions[0].transaction_date is None
    assert parsed.transactions[0].transaction_date_raw is None
    assert len(parsed.warnings) == 1
    assert parsed.warnings[0].code == "missing_transaction_date"
    assert parsed.warnings[0].raw_text == "1 Apple Inc. purchase"


def test_parse_document_text_merges_wrapped_description_lines() -> None:
    parsed = parse_document_text(
        "1 Apple Inc. Class A Common\nStock purchase 05/08/2026 $1,001 - $15,000\n2 Microsoft sale"
    )

    assert [transaction.row_number for transaction in parsed.transactions] == [1, 2]
    assert parsed.transactions[0].description == "Apple Inc. Class A Common Stock"
    assert parsed.transactions[0].raw_text == "1 Apple Inc. Class A Common Stock purchase 05/08/2026 $1,001 - $15,000"


def test_parse_document_text_merges_intermediate_description_lines_without_hints() -> None:
    parsed = parse_document_text(
        "1 Apple Inc. Class A\nCommon Stock\npurchase 05/08/2026 $1,001 - $15,000\n2 Microsoft sale"
    )

    assert [transaction.row_number for transaction in parsed.transactions] == [1, 2]
    assert parsed.transactions[0].description == "Apple Inc. Class A Common Stock"
    assert parsed.transactions[0].raw_text == "1 Apple Inc. Class A Common Stock purchase 05/08/2026 $1,001 - $15,000"


def test_parse_document_text_preserves_trailing_wrapped_row_provenance() -> None:
    parsed = parse_document_text(
        "1 Apple Inc. purchase 05/08/2026 $1,001 - $15,000\nHeld jointly with spouse\n2 Microsoft sale"
    )

    assert [transaction.row_number for transaction in parsed.transactions] == [1, 2]
    assert parsed.transactions[0].description == "Apple Inc."
    assert parsed.transactions[0].raw_text == (
        "1 Apple Inc. purchase 05/08/2026 $1,001 - $15,000 Held jointly with spouse"
    )


def test_parse_document_text_emits_opt_in_row_level_debug_logs(caplog, monkeypatch) -> None:
    monkeypatch.setattr(settings, "log_enable_row_debug", True)
    caplog.set_level(logging.DEBUG, logger="app.parsing.transactions")

    parse_document_text("Header\n1 Unparseable Candidate Row\nFooter")

    debug_records = [record for record in caplog.records if record.getMessage() == "parser_row_diagnostic"]
    assert debug_records
    assert getattr(debug_records[-1], "diagnostic_code", None) == "unparsed_row"
