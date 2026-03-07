from __future__ import annotations

from app.models import ApprovalResult, Finding, Invoice, ValidationResult


class ApprovalAgent:
    scrutiny_threshold = 10_000

    def run(self, invoice: Invoice, validation: ValidationResult) -> ApprovalResult:
        findings: list[Finding] = []

        if validation.is_blocked:
            return ApprovalResult(
                status="rejected",
                rationale="Rejected due to blocking validation errors.",
                findings=findings,
            )

        if any(finding.severity == "fraud_risk" for finding in validation.findings):
            return ApprovalResult(
                status="rejected",
                rationale="Rejected due to fraud risk indicators.",
                findings=findings,
            )

        if (invoice.total_amount or 0) > self.scrutiny_threshold:
            findings.append(
                Finding(
                    "warning",
                    "requires_scrutiny",
                    "Invoice total exceeds the manual scrutiny threshold.",
                    {"threshold": self.scrutiny_threshold, "total_amount": invoice.total_amount},
                )
            )
            return ApprovalResult(
                status="pending_review",
                rationale="Invoice requires additional review before payment.",
                findings=findings,
            )

        return ApprovalResult(
            status="approved",
            rationale="Invoice passed validation and approval rules.",
            findings=findings,
        )
