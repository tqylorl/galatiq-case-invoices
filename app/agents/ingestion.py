from __future__ import annotations

from pathlib import Path

from app.models import Finding, IngestionResult, Invoice
from app.parsers import get_parser_for_path
from app.reasoning.base import IngestionAmbiguityContext, Reasoner
from app.reasoning.rule_based import RuleBasedReasoner


class IngestionAgent:
    def __init__(self, reasoner: Reasoner | None = None) -> None:
        self.reasoner = reasoner or RuleBasedReasoner()

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

        if self._is_ambiguous(invoice):
            suggestions = self.reasoner.resolve_ambiguous_invoice(
                IngestionAmbiguityContext(invoice=invoice)
            )
            applied_fields: list[str] = []
            if not invoice.vendor_name and suggestions.get("vendor_name"):
                invoice.vendor_name = suggestions["vendor_name"]
                applied_fields.append("vendor_name")
            if not invoice.invoice_number and suggestions.get("invoice_number"):
                invoice.invoice_number = suggestions["invoice_number"]
                applied_fields.append("invoice_number")
            if not invoice.due_date and suggestions.get("due_date"):
                invoice.due_date = suggestions["due_date"]
                applied_fields.append("due_date")
            if applied_fields:
                findings.append(
                    Finding(
                        severity="info",
                        code="llm_ambiguity_resolution_applied",
                        message="Applied LLM-assisted extraction for ambiguous invoice fields.",
                        context={"fields": applied_fields},
                    )
                )

        return IngestionResult(invoice=invoice, findings=findings)

    def _is_ambiguous(self, invoice: Invoice) -> bool:
        if invoice.source_format not in {"txt", "pdf"}:
            return False
        return (
            not invoice.vendor_name
            or not invoice.invoice_number
            or not invoice.due_date
            or not invoice.line_items
        )
