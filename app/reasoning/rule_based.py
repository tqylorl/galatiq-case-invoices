from __future__ import annotations

from app.reasoning.base import ApprovalDecisionContext, CritiqueContext


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
