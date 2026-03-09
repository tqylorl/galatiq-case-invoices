from __future__ import annotations

from app.reasoning.base import (
    ApprovalDecisionContext,
    BorderlineTriageContext,
    CritiqueContext,
    ExceptionSummaryContext,
    IngestionAmbiguityContext,
    NoteRiskContext,
    RejectionSummaryContext,
)


class RuleBasedReasoner:
    def build_rationale(self, context: ApprovalDecisionContext) -> str:
        if context.decision == "rejected" and context.decision_reason == "fraud_risk":
            codes = ", ".join(finding.code for finding in context.decisive_findings)
            return f"Rejected due to fraud risk indicators: {codes}."

        if context.decision == "rejected":
            codes = ", ".join(finding.code for finding in context.decisive_findings)
            return f"Rejected due to blocking validation errors: {codes}."

        if context.decision == "pending_review":
            total_amount = context.invoice.total_amount or 0.0
            return (
                f"Invoice requires additional review because total amount "
                f"{total_amount:.2f} exceeds the 10000.00 threshold."
            )

        return "Invoice passed validation and approval rules with no blocking issues."

    def build_critique(self, context: CritiqueContext) -> str:
        if context.blocking_findings and context.fraud_findings:
            return (
                "Critique confirmed the invoice has both blocking errors and fraud indicators; "
                "fraud rationale should take precedence."
            )
        if context.blocking_findings:
            return "Critique confirmed the invoice has blocking validation errors."
        if context.fraud_findings:
            return "Critique confirmed the invoice has fraud risk indicators."
        return "Critique found no blocking issues."

    def resolve_ambiguous_invoice(self, context: IngestionAmbiguityContext) -> dict[str, str]:
        return {}

    def classify_note_risk(self, context: NoteRiskContext) -> str | None:
        if context.heuristic_tokens:
            tokens = ", ".join(context.heuristic_tokens)
            return f"Suspicious free-text note patterns detected: {tokens}."
        return None

    def summarize_rejection(self, context: RejectionSummaryContext) -> str:
        validation_codes = [finding.code for finding in context.validation_findings]
        approval_codes = [finding.code for finding in context.approval_findings]
        code_summary = ", ".join(validation_codes + approval_codes) or "no_codes"
        return (
            f"Invoice {context.invoice.invoice_number or 'UNKNOWN'} was rejected due to: "
            f"{code_summary}."
        )

    def summarize_exceptions(self, context: ExceptionSummaryContext) -> str | None:
        warning_codes = [f.code for f in context.validation_findings if f.severity == "warning"]
        if not warning_codes:
            return None
        return (
            "Manual reviewer attention recommended for warning-level exceptions: "
            + ", ".join(warning_codes)
            + "."
        )

    def triage_borderline(self, context: BorderlineTriageContext) -> bool:
        warning_codes = {f.code for f in context.validation_findings if f.severity == "warning"}
        if warning_codes & {"due_date_missing", "invalid_due_date_format"}:
            return True
        if warning_codes and (context.invoice.total_amount or 0.0) >= 8_000:
            return True
        return False
