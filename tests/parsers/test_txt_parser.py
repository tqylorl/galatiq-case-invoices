from __future__ import annotations

from pathlib import Path

from app.parsers.txt_parser import TextInvoiceParser


def parse_invoice(invoices_dir: Path, invoice_name: str):
    return TextInvoiceParser().parse(invoices_dir / invoice_name)


def write_invoice(tmp_path: Path, text: str) -> Path:
    invoice_path = tmp_path / "invoice.txt"
    invoice_path.write_text(text)
    return invoice_path


def test_txt_parser_normalizes_abbreviated_invoice_number(invoices_dir: Path) -> None:
    invoice = parse_invoice(invoices_dir, "invoice_1002.txt")

    assert invoice.invoice_number == "INV-1002"
    assert invoice.vendor_name == "Gadgets Co."
    assert invoice.total_amount == 15000.0
    assert invoice.line_items[0].item_name == "GadgetX"


def test_txt_parser_parses_clean_invoice_headers_and_items(invoices_dir: Path) -> None:
    invoice = parse_invoice(invoices_dir, "invoice_1001.txt")

    assert invoice.invoice_number == "INV-1001"
    assert invoice.vendor_name == "Widgets Inc."
    assert invoice.invoice_date == "2026-01-15"
    assert invoice.due_date == "2026-02-01"
    assert invoice.payment_terms == "Net 15"
    assert invoice.subtotal == 5000.0
    assert invoice.tax_amount == 0.0
    assert invoice.total_amount == 5000.0
    assert [(item.item_name, item.quantity) for item in invoice.line_items] == [
        ("WidgetA", 10.0),
        ("WidgetB", 5.0),
    ]


def test_txt_parser_preserves_relative_due_date_and_suspicious_note_context(
    invoices_dir: Path,
) -> None:
    invoice = parse_invoice(invoices_dir, "invoice_1003.txt")

    assert invoice.invoice_number == "INV-1003"
    assert invoice.vendor_name == "Fraudster LLC"
    assert invoice.due_date == "yesterday"
    assert invoice.total_amount == 100000.0
    assert invoice.line_items[0].item_name == "FakeItem"
    assert invoice.raw_text is not None
    assert "URGENT - Pay immediately" in invoice.raw_text


def test_txt_parser_handles_email_style_invoice_body(invoices_dir: Path) -> None:
    invoice = parse_invoice(invoices_dir, "invoice_1008.txt")

    assert invoice.invoice_number == "INV-1008"
    assert invoice.vendor_name == "NoProd Industries"
    assert invoice.invoice_date == "2026-01-10"
    assert invoice.due_date == "2026-01-20"
    assert invoice.total_amount == 9900.0
    assert [item.item_name for item in invoice.line_items] == [
        "SuperGizmo",
        "MegaSprocket",
    ]


def test_txt_parser_extracts_shipping_and_true_total(invoices_dir: Path) -> None:
    invoice = parse_invoice(invoices_dir, "invoice_1010.txt")

    assert invoice.invoice_number == "INV-1010"
    assert invoice.vendor_name == "Consolidated Materials Group"
    assert invoice.subtotal == 6700.0
    assert invoice.tax_amount == 335.0
    assert invoice.shipping_amount == 150.0
    assert invoice.total_amount == 7185.0
    assert [item.item_name for item in invoice.line_items] == [
        "WidgetA",
        "WidgetB",
        "GadgetX",
        "WidgetA (rush order)",
    ]


def test_txt_parser_handles_table_layout_invoice(invoices_dir: Path) -> None:
    invoice = parse_invoice(invoices_dir, "invoice_1011.txt")

    assert invoice.invoice_number == "INV-1011"
    assert invoice.vendor_name == "Summit Manufacturing Co."
    assert invoice.subtotal == 3000.0
    assert invoice.tax_amount == 0.0
    assert invoice.total_amount == 3000.0
    assert [(item.item_name, item.line_total) for item in invoice.line_items] == [
        ("WidgetA", 1500.0),
        ("WidgetB", 1500.0),
    ]


def test_txt_parser_normalizes_ocr_style_invoice(invoices_dir: Path) -> None:
    invoice = parse_invoice(invoices_dir, "invoice_1012.txt")

    assert invoice.invoice_number == "INV-1012"
    assert invoice.vendor_name == "QuickShip Distributers"
    assert invoice.invoice_date == "26-Jan-2026"
    assert invoice.due_date == "25-Feb-2026"
    assert invoice.subtotal == 9500.0
    assert invoice.tax_amount == 475.0
    assert invoice.total_amount == 9975.0
    assert [item.item_name for item in invoice.line_items] == [
        "WidgetA",
        "WidgetB",
        "GadgetX",
    ]


def test_match_first_returns_none_when_no_pattern_matches() -> None:
    parser = TextInvoiceParser()

    value = parser._match_first("completely unrelated text", [r"Vendor:\s*(.+)"])

    assert value is None


def test_extract_amount_returns_none_when_amount_is_missing() -> None:
    parser = TextInvoiceParser()

    value = parser._extract_amount("no totals here", [r"Total:\s*\$?([0-9,]+\.\d{2})"])

    assert value is None


def test_extract_items_returns_empty_list_when_no_item_lines_exist() -> None:
    parser = TextInvoiceParser()

    items = parser._extract_items("Vendor: Widgets Inc.\nTotal Amount: $25.00\n")

    assert items == []


def test_extract_items_uses_computed_line_total_when_amount_column_missing() -> None:
    parser = TextInvoiceParser()

    items = parser._extract_items("WidgetA qty: 3 unit price: $250.00")

    assert len(items) == 1
    assert items[0].line_total == 750.0


def test_extract_items_uses_explicit_line_total_when_present() -> None:
    parser = TextInvoiceParser()

    items = parser._extract_items("WidgetA 3 $250.00 $900.00")

    assert len(items) == 1
    assert items[0].line_total == 900.0


def test_parse_leaves_missing_headers_as_none(tmp_path: Path) -> None:
    invoice_path = write_invoice(
        tmp_path,
        "\n".join(
            [
                "INVOICE",
                "",
                "Date: 2026-02-01",
                "WidgetA qty: 2 unit price: $250.00",
                "Total Amount: $500.00",
            ]
        ),
    )

    invoice = TextInvoiceParser().parse(invoice_path)

    assert invoice.invoice_number is None
    assert invoice.vendor_name is None
    assert invoice.due_date is None
    assert invoice.payment_terms is None
    assert invoice.total_amount == 500.0
