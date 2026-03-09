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


@dataclass(slots=True)
class IngestionAmbiguityContext:
    invoice: Invoice


@dataclass(slots=True)
class NoteRiskContext:
    invoice: Invoice
    heuristic_tokens: list[str]


@dataclass(slots=True)
class RejectionSummaryContext:
    invoice: Invoice
    validation_findings: list[Finding]
    approval_findings: list[Finding]


@dataclass(slots=True)
class ExceptionSummaryContext:
    invoice: Invoice
    validation_findings: list[Finding]


@dataclass(slots=True)
class BorderlineTriageContext:
    invoice: Invoice
    validation_findings: list[Finding]


class Reasoner(Protocol):
    def build_rationale(self, context: ApprovalDecisionContext) -> str:
        ...

    def build_critique(self, context: CritiqueContext) -> str:
        ...

    def resolve_ambiguous_invoice(self, context: IngestionAmbiguityContext) -> dict[str, str]:
        ...

    def classify_note_risk(self, context: NoteRiskContext) -> str | None:
        ...

    def summarize_rejection(self, context: RejectionSummaryContext) -> str:
        ...

    def summarize_exceptions(self, context: ExceptionSummaryContext) -> str | None:
        ...

    def triage_borderline(self, context: BorderlineTriageContext) -> bool:
        ...
