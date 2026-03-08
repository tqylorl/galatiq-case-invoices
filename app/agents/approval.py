from __future__ import annotations

from app.models import ApprovalResult, Finding, Invoice, ValidationResult


class ApprovalAgent:
    scrutiny_threshold = 10_000

    def run(self, invoice: Invoice, validation: ValidationResult) -> ApprovalResult:
        approval_findings: list[Finding] = []
        critique = self._critique(validation)
        if critique is not None:
            approval_findings.append(critique)

        blocking_findings = [finding for finding in validation.findings if finding.severity == "error"]
        fraud_findings = [finding for finding in validation.findings if finding.severity == "fraud_risk"]

        if fraud_findings:
            approval_findings.append(
                Finding(
                    "fraud_risk",
                    "rejected_for_fraud_risk",
                    "Approval rejected the invoice because fraud indicators were present.",
                    {"validation_codes": [finding.code for finding in fraud_findings]},
                )
            )
            return ApprovalResult(
                status="rejected",
                rationale=self._build_rationale(
                    "Rejected due to fraud risk indicators",
                    fraud_findings,
                ),
                findings=approval_findings,
            )

        if blocking_findings:
            approval_findings.append(
                Finding(
                    "error",
                    "rejected_for_validation_errors",
                    "Approval rejected the invoice because validation produced blocking errors.",
                    {"validation_codes": [finding.code for finding in blocking_findings]},
                )
            )
            return ApprovalResult(
                status="rejected",
                rationale=self._build_rationale(
                    "Rejected due to blocking validation errors",
                    blocking_findings,
                ),
                findings=approval_findings,
            )

        if (invoice.total_amount or 0) > self.scrutiny_threshold:
            approval_findings.append(
                Finding(
                    "warning",
                    "requires_scrutiny",
                    "Invoice total exceeds the manual scrutiny threshold.",
                    {"threshold": self.scrutiny_threshold, "total_amount": invoice.total_amount},
                )
            )
            return ApprovalResult(
                status="pending_review",
                rationale=(
                    f"Invoice requires additional review because total amount "
                    f"{invoice.total_amount:.2f} exceeds the {self.scrutiny_threshold:.2f} threshold."
                ),
                findings=approval_findings,
            )

        return ApprovalResult(
            status="approved",
            rationale="Invoice passed validation and approval rules with no blocking issues.",
            findings=approval_findings,
        )

    def _critique(self, validation: ValidationResult) -> Finding | None:
        blocking_findings = [finding for finding in validation.findings if finding.severity == "error"]
        fraud_findings = [finding for finding in validation.findings if finding.severity == "fraud_risk"]

        if blocking_findings and fraud_findings:
            return Finding(
                "info",
                "approval_critique",
                "Critique confirmed the invoice has both blocking errors and fraud indicators; fraud rationale should take precedence.",
                {
                    "blocking_error_codes": [finding.code for finding in blocking_findings],
                    "fraud_codes": [finding.code for finding in fraud_findings],
                },
            )

        if blocking_findings:
            return Finding(
                "info",
                "approval_critique",
                "Critique confirmed the invoice has blocking validation errors.",
                {"blocking_error_codes": [finding.code for finding in blocking_findings]},
            )

        if fraud_findings:
            return Finding(
                "info",
                "approval_critique",
                "Critique confirmed the invoice has fraud risk indicators.",
                {"fraud_codes": [finding.code for finding in fraud_findings]},
            )

        return None

    def _build_rationale(self, prefix: str, findings: list[Finding]) -> str:
        codes = ", ".join(finding.code for finding in findings)
        return f"{prefix}: {codes}."
