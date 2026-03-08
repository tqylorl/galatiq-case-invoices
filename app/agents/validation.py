from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.db import get_inventory_stock
from app.models import Finding, Invoice, ValidationResult


class ValidationAgent:
    DATE_FORMATS = (
        "%Y-%m-%d",
        "%b %d %Y",
        "%B %d, %Y",
        "%d-%b-%Y",
    )
    RELATIVE_DATE_TOKENS = {"yesterday", "today", "tomorrow"}
    URGENT_LANGUAGE_TOKENS = (
        "urgent",
        "immediately",
        "wire transfer",
        "avoid penalties",
    )

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def run(self, invoice: Invoice) -> ValidationResult:
        findings: list[Finding] = []

        if not invoice.vendor_name:
            findings.append(
                Finding("error", "vendor_missing", "Invoice vendor is required.")
            )

        if not invoice.due_date:
            findings.append(
                Finding("warning", "due_date_missing", "Invoice due date is missing.")
            )
        else:
            findings.extend(self._validate_due_date(invoice.due_date))

        findings.extend(self._validate_totals(invoice))
        findings.extend(self._detect_fraud_signals(invoice))

        for item in invoice.line_items:
            if item.quantity is None or item.quantity <= 0:
                findings.append(
                    Finding(
                        "error",
                        "invalid_quantity",
                        f"Item {item.item_name} has an invalid quantity.",
                        {"item_name": item.item_name, "quantity": item.quantity},
                    )
                )
                continue

            stock = get_inventory_stock(self.db_path, item.item_name)
            if stock is None:
                findings.append(
                    Finding(
                        "error",
                        "unknown_item",
                        f"Item {item.item_name} was not found in inventory.",
                        {"item_name": item.item_name},
                    )
                )
            else:
                if stock == 0:
                    findings.append(
                        Finding(
                            "fraud_risk",
                            "zero_stock_item",
                            f"Item {item.item_name} is listed with zero stock.",
                            {"item_name": item.item_name},
                        )
                    )

                if item.quantity > stock:
                    findings.append(
                        Finding(
                            "error",
                            "insufficient_stock",
                            f"Item {item.item_name} exceeds available stock.",
                            {"item_name": item.item_name, "requested": item.quantity, "stock": stock},
                        )
                    )

        is_blocked = any(finding.severity == "error" for finding in findings)
        return ValidationResult(findings=findings, is_blocked=is_blocked)

    def _validate_due_date(self, due_date: str) -> list[Finding]:
        normalized = due_date.strip().lower()
        if normalized in self.RELATIVE_DATE_TOKENS:
            return [
                Finding(
                    "fraud_risk",
                    "suspicious_due_date",
                    "Invoice due date uses a relative date expression.",
                    {"due_date": due_date},
                )
            ]

        for date_format in self.DATE_FORMATS:
            try:
                datetime.strptime(due_date, date_format)
                return []
            except ValueError:
                continue

        return [
            Finding(
                "warning",
                "invalid_due_date_format",
                "Invoice due date is not in a recognized format.",
                {"due_date": due_date},
            )
        ]

    def _validate_totals(self, invoice: Invoice) -> list[Finding]:
        findings: list[Finding] = []
        computed_subtotal = self._compute_subtotal(invoice)

        if computed_subtotal is not None and invoice.subtotal is not None:
            if not self._amounts_match(computed_subtotal, invoice.subtotal):
                findings.append(
                    Finding(
                        "error",
                        "subtotal_mismatch",
                        "Invoice subtotal does not match the sum of line items.",
                        {"computed_subtotal": computed_subtotal, "invoice_subtotal": invoice.subtotal},
                    )
                )

        expected_total_base = invoice.subtotal if invoice.subtotal is not None else computed_subtotal
        if expected_total_base is not None and invoice.total_amount is not None:
            expected_total = expected_total_base + (invoice.tax_amount or 0.0) + (invoice.shipping_amount or 0.0)
            if not self._amounts_match(expected_total, invoice.total_amount):
                findings.append(
                    Finding(
                        "error",
                        "total_mismatch",
                        "Invoice total does not reconcile with subtotal, tax, and shipping.",
                        {"expected_total": expected_total, "invoice_total": invoice.total_amount},
                    )
                )

        if invoice.total_amount is not None and invoice.total_amount < 0:
            findings.append(
                Finding(
                    "error",
                    "invalid_total",
                    "Invoice total amount cannot be negative.",
                    {"invoice_total": invoice.total_amount},
                )
            )

        return findings

    def _detect_fraud_signals(self, invoice: Invoice) -> list[Finding]:
        if not invoice.raw_text:
            return []

        raw_text = invoice.raw_text.lower()
        matched_tokens = [token for token in self.URGENT_LANGUAGE_TOKENS if token in raw_text]
        if not matched_tokens:
            return []

        return [
            Finding(
                "fraud_risk",
                "urgent_payment_language",
                "Invoice contains urgent payment or wire transfer language.",
                {"matched_terms": matched_tokens},
            )
        ]

    def _compute_subtotal(self, invoice: Invoice) -> float | None:
        subtotal = 0.0
        has_amount = False
        for item in invoice.line_items:
            line_total = item.line_total
            if line_total is None and item.quantity is not None and item.unit_price is not None:
                line_total = float(item.quantity) * item.unit_price
            if line_total is None:
                continue
            has_amount = True
            subtotal += line_total

        return subtotal if has_amount else None

    def _amounts_match(self, left: float, right: float, tolerance: float = 0.01) -> bool:
        return abs(left - right) <= tolerance
