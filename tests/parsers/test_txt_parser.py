from __future__ import annotations

from pathlib import Path

from app.parsers.txt_parser import TextInvoiceParser


def parse_invoice(invoices_dir: Path, invoice_name: str):
    return TextInvoiceParser().parse(invoices_dir / invoice_name)


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
