from __future__ import annotations

from pathlib import Path

from app.config import AppConfig
from app.db import bootstrap_inventory_db
from app.orchestrator import InvoiceProcessor


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_invoice(invoice_name: str, tmp_path: Path):
    db_path = tmp_path / "inventory.db"
    bootstrap_inventory_db(db_path)

    config = AppConfig(
        invoice_path=REPO_ROOT / "data" / "invoices" / invoice_name,
        db_path=db_path,
        output_format="json",
    )
    processor = InvoiceProcessor(config)
    return processor.process()


def test_json_invoice_approves(tmp_path: Path) -> None:
    result = run_invoice("invoice_1004.json", tmp_path)

    assert result.status == "approved"
    assert result.payment is not None
    assert result.invoice.vendor_name == "Precision Parts Ltd."
    assert result.invoice.total_amount == 1890.0


def test_text_invoice_rejects_when_stock_is_insufficient(tmp_path: Path) -> None:
    result = run_invoice("invoice_1002.txt", tmp_path)

    assert result.status == "rejected"
    assert result.payment is None
    assert any(
        finding.code == "insufficient_stock"
        for finding in result.validation.findings
    )


def test_xml_invoice_approves(tmp_path: Path) -> None:
    result = run_invoice("invoice_1014.xml", tmp_path)

    assert result.status == "approved"
    assert result.payment is not None
    assert result.invoice.currency == "EUR"


def test_json_invoice_with_negative_quantity_rejects(tmp_path: Path) -> None:
    result = run_invoice("invoice_1009.json", tmp_path)

    assert result.status == "rejected"
    assert result.payment is None
    assert any(
        finding.code == "invalid_quantity"
        for finding in result.validation.findings
    )
