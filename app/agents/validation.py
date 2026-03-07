from __future__ import annotations

from pathlib import Path

from app.db import get_inventory_stock
from app.models import Finding, Invoice, ValidationResult


class ValidationAgent:
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
            elif item.quantity > stock:
                findings.append(
                    Finding(
                        "error",
                        "insufficient_stock",
                        f"Item {item.item_name} exceeds available stock.",
                        {"item_name": item.item_name, "requested": item.quantity, "stock": stock},
                    )
                )
            elif stock == 0:
                findings.append(
                    Finding(
                        "fraud_risk",
                        "zero_stock_item",
                        f"Item {item.item_name} is listed with zero stock.",
                        {"item_name": item.item_name},
                    )
                )

        is_blocked = any(finding.severity == "error" for finding in findings)
        return ValidationResult(findings=findings, is_blocked=is_blocked)
