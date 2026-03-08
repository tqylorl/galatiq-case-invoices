from __future__ import annotations

from app.agents.approval import ApprovalAgent
from app.models import ApprovalResult, Finding, Invoice, ValidationResult


def make_invoice(total_amount: float | None = 1000.0) -> Invoice:
    return Invoice(vendor_name="Precision Parts Ltd.", due_date="2026-02-22", total_amount=total_amount)


def test_approval_rejects_fraud_risk_with_specific_rationale() -> None:
    validation = ValidationResult(
        findings=[
            Finding("fraud_risk", "urgent_payment_language", "Urgent language detected."),
            Finding("error", "insufficient_stock", "Quantity exceeds stock."),
        ],
        is_blocked=True,
    )

    result = ApprovalAgent().run(make_invoice(), validation)

    assert result.status == "rejected"
    assert "fraud risk indicators" in result.rationale.lower()
    assert "urgent_payment_language" in result.rationale
    assert any(finding.code == "approval_critique" for finding in result.findings)
    assert any(finding.code == "rejected_for_fraud_risk" for finding in result.findings)


def test_approval_rejects_blocking_errors_when_no_fraud_exists() -> None:
    validation = ValidationResult(
        findings=[Finding("error", "unknown_item", "Item was not found in inventory.")],
        is_blocked=True,
    )

    result = ApprovalAgent().run(make_invoice(), validation)

    assert result.status == "rejected"
    assert "blocking validation errors" in result.rationale.lower()
    assert "unknown_item" in result.rationale
    assert any(finding.code == "rejected_for_validation_errors" for finding in result.findings)


def test_approval_marks_high_value_invoice_pending_review() -> None:
    validation = ValidationResult(findings=[], is_blocked=False)

    result = ApprovalAgent().run(make_invoice(total_amount=15225.0), validation)

    assert result.status == "pending_review"
    assert "exceeds the 10000.00 threshold" in result.rationale
    assert any(finding.code == "requires_scrutiny" for finding in result.findings)


def test_approval_approves_clean_invoice() -> None:
    validation = ValidationResult(findings=[], is_blocked=False)

    result = ApprovalAgent().run(make_invoice(total_amount=1890.0), validation)

    assert result.status == "approved"
    assert "no blocking issues" in result.rationale.lower()
    assert result.findings == []
