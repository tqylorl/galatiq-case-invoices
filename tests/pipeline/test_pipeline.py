from __future__ import annotations

import sys
from types import SimpleNamespace


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


def test_json_invoice_approves(run_invoice) -> None:
    result = run_invoice("invoice_1004.json")

    assert result.status == "approved"
    assert result.payment is not None
    assert result.invoice.vendor_name == "Precision Parts Ltd."
    assert result.invoice.total_amount == 1890.0


def test_text_invoice_rejects_when_stock_is_insufficient(run_invoice) -> None:
    result = run_invoice("invoice_1002.txt")

    assert result.status == "rejected"
    assert result.payment is None
    assert any(
        finding.code == "insufficient_stock"
        for finding in result.validation.findings
    )


def test_xml_invoice_approves(run_invoice) -> None:
    result = run_invoice("invoice_1014.xml")

    assert result.status == "approved"
    assert result.payment is not None
    assert result.invoice.currency == "EUR"


def test_json_invoice_with_negative_quantity_rejects(run_invoice) -> None:
    result = run_invoice("invoice_1009.json")

    assert result.status == "rejected"
    assert result.payment is None
    assert any(
        finding.code == "invalid_quantity"
        for finding in result.validation.findings
    )


def test_text_invoice_rejects_for_fraud_risk(run_invoice) -> None:
    result = run_invoice("invoice_1003.txt")

    assert result.status == "rejected"
    assert result.payment is None
    assert "fraud risk indicators" in result.approval.rationale.lower()
    assert any(
        finding.code == "urgent_payment_language"
        for finding in result.validation.findings
    )


def test_text_invoice_rejects_for_unknown_items(run_invoice) -> None:
    result = run_invoice("invoice_1008.txt")

    assert result.status == "rejected"
    assert result.payment is None
    assert sum(
        1 for finding in result.validation.findings if finding.code == "unknown_item"
    ) == 2


def test_json_invoice_can_reach_pending_review_when_inventory_allows_it(
    run_invoice, set_inventory_stock
) -> None:
    set_inventory_stock("GadgetX", 8)

    result = run_invoice("invoice_1005.json")

    assert result.status == "pending_review"
    assert result.payment is None
    assert any(
        finding.code == "requires_scrutiny"
        for finding in result.approval.findings
    )


def test_pdf_invoice_runs_end_to_end_with_fake_pdf_reader(run_invoice, monkeypatch) -> None:
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
                    "Subtotal: $3,000.00",
                    "Tax (0%): $0.00",
                    "Total Amount: $3,000.00",
                    "Payment Terms: Net 30",
                ]
            )
        ],
    )

    result = run_invoice("invoice_1011.pdf")

    assert result.status == "approved"
    assert result.payment is not None
    assert result.invoice.source_format == "pdf"
    assert result.invoice.invoice_number == "INV-1011"
