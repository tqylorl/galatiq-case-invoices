from __future__ import annotations

from pathlib import Path

from app.models import Finding, IngestionResult, Invoice
from app.parsers import get_parser_for_path


class IngestionAgent:
    def run(self, invoice_path: Path) -> IngestionResult:
        parser = get_parser_for_path(invoice_path)
        invoice = parser.parse(invoice_path)
        invoice.source_path = str(invoice_path)
        invoice.source_format = invoice_path.suffix.lower().lstrip(".")

        findings: list[Finding] = []
        if not invoice.vendor_name:
            findings.append(
                Finding(
                    severity="warning",
                    code="missing_vendor",
                    message="Vendor name is missing from the parsed invoice.",
                )
            )

        if not invoice.invoice_number:
            findings.append(
                Finding(
                    severity="warning",
                    code="missing_invoice_number",
                    message="Invoice number is missing from the parsed invoice.",
                )
            )

        return IngestionResult(invoice=invoice, findings=findings)
