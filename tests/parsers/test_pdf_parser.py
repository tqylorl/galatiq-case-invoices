from __future__ import annotations

import builtins
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.parsers.pdf_parser import PdfInvoiceParser


def install_fake_pypdf(monkeypatch, extracted_pages: list[str | None]) -> None:
    class FakePage:
        def __init__(self, text: str | None) -> None:
            self.text = text

        def extract_text(self) -> str | None:
            return self.text

    class FakePdfReader:
        def __init__(self, path: str) -> None:
            self.path = path
            self.pages = [FakePage(text) for text in extracted_pages]

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=FakePdfReader))


def test_pdf_parser_raises_clear_error_when_pypdf_is_unavailable(
    monkeypatch, invoices_dir: Path
) -> None:
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pypdf":
            raise ImportError("missing pypdf")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.delitem(sys.modules, "pypdf", raising=False)

    with pytest.raises(RuntimeError, match="PDF parsing requires the 'pypdf' package"):
        PdfInvoiceParser().parse(invoices_dir / "invoice_1011.pdf")


def test_pdf_parser_parses_extracted_text_into_invoice_fields(monkeypatch, invoices_dir: Path) -> None:
    install_fake_pypdf(
        monkeypatch,
        [
            "\n".join(
                [
                    "INVOICE",
                    "",
                    "Invoice Number: INV-1011",
                    "Vendor: Summit Manufacturing Co.",
                    "Date: 2026-01-20",
                    "Due Date: 2026-02-20",
                    "",
                    "WidgetA qty: 6 unit price: $250.00",
                    "WidgetB qty: 3 unit price: $500.00",
                    "Total Amount: $3,000.00",
                    "Payment Terms: Net 30",
                ]
            )
        ],
    )

    invoice = PdfInvoiceParser().parse(invoices_dir / "invoice_1011.pdf")

    assert invoice.invoice_number == "INV-1011"
    assert invoice.vendor_name == "Summit Manufacturing Co."
    assert invoice.total_amount == 3000.0
    assert [item.item_name for item in invoice.line_items] == ["WidgetA", "WidgetB"]


def test_pdf_parser_handles_multi_page_text_and_none_page_values(
    monkeypatch, tmp_path: Path
) -> None:
    install_fake_pypdf(
        monkeypatch,
        [
            "Vendor: Example Co.\nInvoice Number: INV-9000",
            None,
            "WidgetA qty: 2 unit price: $250.00\nTotal Amount: $500.00",
        ],
    )
    pdf_path = tmp_path / "invoice.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake pdf bytes")

    invoice = PdfInvoiceParser().parse(pdf_path)

    assert invoice.raw_text == (
        "Vendor: Example Co.\nInvoice Number: INV-9000\n\nWidgetA qty: 2 unit price: $250.00\nTotal Amount: $500.00"
    )
    assert invoice.invoice_number == "INV-9000"
    assert invoice.vendor_name == "Example Co."
    assert invoice.total_amount == 500.0
    assert invoice.line_items[0].item_name == "WidgetA"


def test_pdf_parser_returns_sparse_invoice_when_text_is_unstructured(
    monkeypatch, tmp_path: Path
) -> None:
    install_fake_pypdf(monkeypatch, ["completely unrelated text"])
    pdf_path = tmp_path / "invoice.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake pdf bytes")

    invoice = PdfInvoiceParser().parse(pdf_path)

    assert invoice.raw_text == "completely unrelated text"
    assert invoice.invoice_number is None
    assert invoice.vendor_name is None
    assert invoice.total_amount is None
