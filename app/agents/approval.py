from __future__ import annotations

from app.models import ApprovalResult, Finding, Invoice, ValidationResult
from app.reasoning.base import ApprovalDecisionContext, CritiqueContext, Reasoner
from app.reasoning.rule_based import RuleBasedReasoner


class ApprovalAgent:
    scrutiny_threshold = 10_000

    def __init__(self, reasoner: Reasoner | None = None) -> None:
        self.reasoner = reasoner or RuleBasedReasoner()

    def run(self, invoice: Invoice, validation: ValidationResult) -> ApprovalResult:
        approval_findings: list[Finding] = []
        blocking_findings = [finding for finding in validation.findings if finding.severity == "error"]
        fraud_findings = [finding for finding in validation.findings if finding.severity == "fraud_risk"]
        critique = self._critique(invoice, validation, blocking_findings, fraud_findings)
        if critique is not None:
            approval_findings.append(critique)

        if fraud_findings:
            approval_findings.append(
                Finding(
                    "fraud_risk",
                    "rejected_for_fraud_risk",
                    "Approval rejected the invoice because fraud indicators were present.",
                    {"validation_codes": [finding.code for finding in fraud_findings]},
                )
            )
            rationale = self.reasoner.build_rationale(
                ApprovalDecisionContext(
                    invoice=invoice,
                    validation=validation,
                    decision="rejected",
                    decision_reason="fraud_risk",
                    decisive_findings=fraud_findings,
                )
            )
            return ApprovalResult(
                status="rejected",
                rationale=rationale,
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
            rationale = self.reasoner.build_rationale(
                ApprovalDecisionContext(
                    invoice=invoice,
                    validation=validation,
                    decision="rejected",
                    decision_reason="validation_errors",
                    decisive_findings=blocking_findings,
                )
            )
            return ApprovalResult(
                status="rejected",
                rationale=rationale,
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
            rationale = self.reasoner.build_rationale(
                ApprovalDecisionContext(
                    invoice=invoice,
                    validation=validation,
                    decision="pending_review",
                    decision_reason="scrutiny_threshold",
                    decisive_findings=approval_findings[-1:],
                )
            )
            return ApprovalResult(
                status="pending_review",
                rationale=rationale,
                findings=approval_findings,
            )

        rationale = self.reasoner.build_rationale(
            ApprovalDecisionContext(
                invoice=invoice,
                validation=validation,
                decision="approved",
                decision_reason="clear",
                decisive_findings=[],
            )
        )
        return ApprovalResult(
            status="approved",
            rationale=rationale,
            findings=approval_findings,
        )

    def _critique(
        self,
        invoice: Invoice,
        validation: ValidationResult,
        blocking_findings: list[Finding],
        fraud_findings: list[Finding],
    ) -> Finding | None:
        if not blocking_findings and not fraud_findings:
            return None

        summary = self.reasoner.build_critique(
            CritiqueContext(
                invoice=invoice,
                validation=validation,
                blocking_findings=blocking_findings,
                fraud_findings=fraud_findings,
            )
        )
        context: dict[str, list[str]] = {}
        if blocking_findings:
            context["blocking_error_codes"] = [finding.code for finding in blocking_findings]
        if fraud_findings:
            context["fraud_codes"] = [finding.code for finding in fraud_findings]
        return Finding("info", "approval_critique", summary, context)
