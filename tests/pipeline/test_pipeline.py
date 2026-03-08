from __future__ import annotations

from pathlib import Path


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
