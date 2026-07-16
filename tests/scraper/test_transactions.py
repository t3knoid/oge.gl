import logging

import pytest

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
    assert row["amount_text"] == "$1,001-$15,000"
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
    assert row["amount_text"] == "$15,001-$50,000"
    assert row["amount_min"] == 15001
    assert row["amount_max"] == 50000


def test_parse_row_line_recovers_camden_property_trust_ocr_date_token() -> None:
    row = parse_row_line("320 CAMDEN PROPERTY TRUST sale 4127=6 Yos $1 001-$15000.")

    assert row is not None
    assert row["num"] == 320
    assert row["transaction_date"] == "2026-04-27"
    assert row["transaction_date_raw"] == "4127=6"
    assert row["amount_text"] == "$1,001-$15,000"
    assert row["amount_min"] == 1001
    assert row["amount_max"] == 15000


def test_parse_row_line_recovers_iqvia_ocr_date_and_amount_range() -> None:
    row = parse_row_line("725 IQVIA HOLDINGS INC sale 4110/2026 Yos $1 001 -$15 000")

    assert row is not None
    assert row["num"] == 725
    assert row["transaction_date"] == "2026-04-10"
    assert row["transaction_date_raw"] == "4110/2026"
    assert row["amount_text"] == "$1,001-$15,000"
    assert row["amount_min"] == 1001
    assert row["amount_max"] == 15000


def test_parse_row_line_recovers_cbre_unsolicited_ocr_date_and_amount_range() -> None:
    row = parse_row_line("726 CBRE GROUP INC CL A UNSOLICITED DUrchDSO 3/2512026 Yoo $15.001 • $50,000")

    assert row is not None
    assert row["num"] == 726
    assert row["transaction_date"] == "2026-03-25"
    assert row["transaction_date_raw"] == "3/2512026"
    assert row["amount_text"] == "$15,001-$50,000"
    assert row["amount_min"] == 15001
    assert row["amount_max"] == 50000


def test_parse_row_line_recovers_bullet_separated_amount_with_date() -> None:
    row = parse_row_line("336 SOME CO sale 4127/2026 Yes $15 001 • $50 000")

    assert row is not None
    assert row["num"] == 336
    assert row["transaction_date"] == "2026-04-27"
    assert row["transaction_date_raw"] == "4127/2026"
    assert row["amount_text"] == "$15,001-$50,000"
    assert row["amount_min"] == 15001
    assert row["amount_max"] == 50000


@pytest.mark.parametrize(
    ("line", "expected_num", "expected_trade_type", "expected_date_raw", "expected_date"),
    [
        (
            "143 AMAZON.COM INC lourchase 4/28/2026 Yos $1 001 -$15 000",
            143,
            "purchase",
            "4/28/2026",
            "2026-04-28",
        ),
        (
            "145 AMAZON.COM INC sale 4/20121)26 Yes $1 001 • $15 000",
            145,
            "sale",
            "4/20/2026",
            "2026-04-20",
        ),
        (
            "146 AMAZON.COM INC IDUrchase 4/27121)26 Yes $15 001 • $50 000",
            146,
            "purchase",
            "4/27/2026",
            "2026-04-27",
        ),
    ],
)
def test_parse_row_line_recovers_amazon_ocr_row_variants(
    line: str,
    expected_num: int,
    expected_trade_type: str,
    expected_date_raw: str,
    expected_date: str,
) -> None:
    row = parse_row_line(line)

    assert row is not None
    assert row["num"] == expected_num
    assert row["trade_type"] == expected_trade_type
    assert row["transaction_date_raw"] == expected_date_raw
    assert row["transaction_date"] == expected_date


@pytest.mark.parametrize(
    ("line", "expected_num", "expected_amount_text", "expected_min", "expected_max"),
    [
        (
            "16 CLOROX COMPANY sale 4/17/2026 Yos $100 001 • $250 000",
            16,
            "$100,001-$250,000",
            100001,
            250000,
        ),
        (
            "21 ECOLAB INC sale 4/17/2026 Yos $250 001 • $500 000",
            21,
            "$250,001-$500,000",
            250001,
            500000,
        ),
        (
            "26 GE HEALTHCARE TECHNOLOGIES INC sale 4/17/2026 Yes $100 001 • $250 000",
            26,
            "$100,001-$250,000",
            100001,
            250000,
        ),
    ],
)
def test_parse_row_line_recovers_more_clean_enough_rows_from_same_filing(
    line: str,
    expected_num: int,
    expected_amount_text: str,
    expected_min: int,
    expected_max: int,
) -> None:
    row = parse_row_line(line)

    assert row is not None
    assert row["num"] == expected_num
    assert row["transaction_date"] == "2026-04-17"
    assert row["transaction_date_raw"] == "4/17/2026"
    assert row["amount_text"] == expected_amount_text
    assert row["amount_min"] == expected_min
    assert row["amount_max"] == expected_max


@pytest.mark.parametrize(
    ("line", "expected_num", "expected_amount_text", "expected_min", "expected_max"),
    [
        (
            "2 ADOBE INC sale 4/17/2026 Yos $1,000 001 • $5,000 000",
            2,
            "$1,000,001-$5,000,000",
            1000001,
            5000000,
        ),
        (
            "13 BOSTON SCIENTIFIC CORP COM sale 4/17/2026 Yos $500 001 • $1 000 000",
            13,
            "$500,001-$1,000,000",
            500001,
            1000000,
        ),
        (
            "14 BROADRIDGE FINL SOLUTIONS INC sale 4/17/2026 Yos $15 001 • $50 000",
            14,
            "$15,001-$50,000",
            15001,
            50000,
        ),
    ],
)
def test_parse_row_line_recovers_more_noisy_rows_from_same_filing(
    line: str,
    expected_num: int,
    expected_amount_text: str,
    expected_min: int,
    expected_max: int,
) -> None:
    row = parse_row_line(line)

    assert row is not None
    assert row["num"] == expected_num
    assert row["transaction_date"] == "2026-04-17"
    assert row["transaction_date_raw"] == "4/17/2026"
    assert row["amount_text"] == expected_amount_text
    assert row["amount_min"] == expected_min
    assert row["amount_max"] == expected_max


@pytest.mark.parametrize(
    ("line", "expected_num", "expected_date", "expected_date_raw", "expected_amount_text", "expected_min", "expected_max"),
    [
        (
            "96 ADOBE INC. /DELAWARE) sale 4127/2026 Yes $50 001 -$100 000",
            96,
            "2026-04-27",
            "4127/2026",
            "$50,001-$100,000",
            50001,
            100000,
        ),
        (
            "167 AMPHENOL CORP NEW CL A sale 4127/2026 Vos $15,001 -$50 000",
            167,
            "2026-04-27",
            "4127/2026",
            "$15,001-$50,000",
            15001,
            50000,
        ),
        (
            "223 AUTODESK INC sale 4127/2026 Yes $50 001 -$100 000",
            223,
            "2026-04-27",
            "4127/2026",
            "$50,001-$100,000",
            50001,
            100000,
        ),
        (
            "272 BLOCK INC CL A sale 4127/2026 Yes $50001-$100000",
            272,
            "2026-04-27",
            "4127/2026",
            "$50,001-$100,000",
            50001,
            100000,
        ),
    ],
)
def test_parse_row_line_recovers_additional_ocr_rows_from_same_filing(
    line: str,
    expected_num: int,
    expected_date: str,
    expected_date_raw: str,
    expected_amount_text: str,
    expected_min: int,
    expected_max: int,
) -> None:
    row = parse_row_line(line)

    assert row is not None
    assert row["num"] == expected_num
    assert row["transaction_date"] == expected_date
    assert row["transaction_date_raw"] == expected_date_raw
    assert row["amount_text"] == expected_amount_text
    assert row["amount_min"] == expected_min
    assert row["amount_max"] == expected_max


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


def test_parse_document_text_does_not_merge_disclaimer_boilerplate_into_row() -> None:
    parsed = parse_document_text(
        "1 Apple Inc. purchase 05/08/2026 $1,001 - $15,000\n"
        "U.S.C. § 13101 et seq., and 5 C.F.R. Part 2634 of the U.S. Office of Government Ethics regulations require the reporting of this information."
    )

    assert len(parsed.transactions) == 1
    assert parsed.transactions[0].description == "Apple Inc."
    assert parsed.transactions[0].raw_text == "1 Apple Inc. purchase 05/08/2026 $1,001 - $15,000"
    assert len(parsed.warnings) == 0


def test_parse_document_text_splits_ocr_row_prefix_from_previous_transaction() -> None:
    parsed = parse_document_text(
        "1271 COMSTOCK RES INC lourchoso 3/30/2026 Vos $15.001 • $50,000\n"
        "12n AXON ENTERPRISE INC COM UNSOLICITED lourchaso 3/2/2026 Vos $15,001 -$50,000\n"
        "1273 MARATHON PETROLEUM CO UNSOLICITED IPUrt:huo 3/2/2026 Vos $15,001 -$50.000"
    )

    assert [transaction.row_number for transaction in parsed.transactions] == [1271, 1273]
    assert parsed.transactions[0].description == "COMSTOCK RES INC"
    assert parsed.transactions[0].trade_type == "purchase"
    assert parsed.transactions[0].transaction_date == "2026-03-30"
    assert parsed.transactions[0].transaction_date_raw == "3/30/2026"


def test_parse_document_text_recovers_wrapped_amount_range_without_notification_prefix() -> None:
    parsed = parse_document_text(
        "3 Arthur Ventures III, LP - PureSpectrum (market See Endnote Sale 01/22/2026 No $1,000,001 -\n"
        "research platform) $5,000,000"
    )

    assert [transaction.row_number for transaction in parsed.transactions] == [3]
    assert parsed.transactions[0].amount_text == "$1,000,001-$5,000,000"
    assert parsed.transactions[0].amount_min == 1000001
    assert parsed.transactions[0].amount_max == 5000000
