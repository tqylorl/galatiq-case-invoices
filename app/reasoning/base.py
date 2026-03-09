from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Finding, Invoice, ValidationResult


@dataclass(slots=True)
class ApprovalDecisionContext:
    invoice: Invoice
    validation: ValidationResult
    decision: str
    decision_reason: str
    decisive_findings: list[Finding]


@dataclass(slots=True)
class CritiqueContext:
    invoice: Invoice
    validation: ValidationResult
    blocking_findings: list[Finding]
    fraud_findings: list[Finding]


class Reasoner(Protocol):
    def build_rationale(self, context: ApprovalDecisionContext) -> str:
        ...

    def build_critique(self, context: CritiqueContext) -> str:
        ...
