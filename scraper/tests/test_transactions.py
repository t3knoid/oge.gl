from app.parsing.transactions import extract_rows_from_text, parse_row_line


def test_parse_row_line_extracts_transaction_fields() -> None:
    row = parse_row_line("1 Apple Inc. purchase 05/08/2026 $1,001 - $15,000")

    assert row is not None
    assert row["num"] == 1
    assert row["issuer"] == "Apple Inc."
    assert row["action"] == "purchase"


def test_extract_rows_from_text_ignores_non_transaction_lines() -> None:
    text = "Header line\n1 Apple Inc. purchase\nFooter line\n2 Microsoft sale"

    rows = extract_rows_from_text(text)

    assert [row["num"] for row in rows] == [1, 2]
