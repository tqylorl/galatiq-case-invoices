from __future__ import annotations

from pathlib import Path

from app.agents.validation import ValidationAgent
from app.models import Invoice, LineItem


def test_validation_flags_unknown_item(seeded_db_path: Path) -> None:
    invoice = Invoice(
        vendor_name="NoProd Industries",
        due_date="2026-01-20",
        line_items=[LineItem(item_name="SuperGizmo", quantity=2, unit_price=400.0, line_total=800.0)],
        subtotal=800.0,
        total_amount=800.0,
    )

    result = ValidationAgent(seeded_db_path).run(invoice)

    assert result.is_blocked is True
    assert any(finding.code == "unknown_item" for finding in result.findings)


def test_validation_flags_zero_stock_relative_due_date_and_urgent_language(
    seeded_db_path: Path,
) -> None:
    invoice = Invoice(
        vendor_name="Fraudster LLC",
        due_date="yesterday",
        line_items=[LineItem(item_name="FakeItem", quantity=1, unit_price=1000.0, line_total=1000.0)],
        subtotal=1000.0,
        total_amount=1000.0,
        raw_text="URGENT - Pay immediately. Wire transfer preferred to avoid penalties.",
    )

    result = ValidationAgent(seeded_db_path).run(invoice)

    assert any(finding.code == "suspicious_due_date" for finding in result.findings)
    assert any(finding.code == "urgent_payment_language" for finding in result.findings)
    assert any(finding.code == "zero_stock_item" for finding in result.findings)
    assert any(finding.code == "insufficient_stock" for finding in result.findings)


def test_validation_flags_missing_vendor_due_date_and_negative_total(
    seeded_db_path: Path,
) -> None:
    invoice = Invoice(
        vendor_name=None,
        due_date=None,
        line_items=[LineItem(item_name="WidgetA", quantity=-5, unit_price=250.0, line_total=-1250.0)],
        subtotal=-1250.0,
        total_amount=-250.0,
    )

    result = ValidationAgent(seeded_db_path).run(invoice)

    assert result.is_blocked is True
    assert any(finding.code == "vendor_missing" for finding in result.findings)
    assert any(finding.code == "due_date_missing" for finding in result.findings)
    assert any(finding.code == "invalid_quantity" for finding in result.findings)
    assert any(finding.code == "invalid_total" for finding in result.findings)


def test_validation_flags_subtotal_and_total_mismatches(seeded_db_path: Path) -> None:
    invoice = Invoice(
        vendor_name="Precision Parts Ltd.",
        due_date="2026-02-22",
        line_items=[
            LineItem(item_name="WidgetA", quantity=3, unit_price=250.0, line_total=750.0),
            LineItem(item_name="WidgetB", quantity=2, unit_price=500.0, line_total=1000.0),
        ],
        subtotal=1900.0,
        tax_amount=140.0,
        shipping_amount=25.0,
        total_amount=1890.0,
    )

    result = ValidationAgent(seeded_db_path).run(invoice)

    assert result.is_blocked is True
    assert any(finding.code == "subtotal_mismatch" for finding in result.findings)
    assert any(finding.code == "total_mismatch" for finding in result.findings)


def test_validation_accepts_reconciling_invoice(seeded_db_path: Path) -> None:
    invoice = Invoice(
        vendor_name="Precision Parts Ltd.",
        due_date="2026-02-22",
        line_items=[
            LineItem(item_name="WidgetA", quantity=3, unit_price=250.0, line_total=750.0),
            LineItem(item_name="WidgetB", quantity=2, unit_price=500.0, line_total=1000.0),
        ],
        subtotal=1750.0,
        tax_amount=140.0,
        total_amount=1890.0,
    )

    result = ValidationAgent(seeded_db_path).run(invoice)

    assert result.is_blocked is False
    assert not any(
        finding.code in {"subtotal_mismatch", "total_mismatch", "invalid_due_date_format"}
        for finding in result.findings
    )
