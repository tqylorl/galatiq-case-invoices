from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class LineItem:
    item_name: str
    quantity: float | int | None = None
    unit_price: float | None = None
    line_total: float | None = None
    notes: str | None = None


@dataclass(slots=True)
class Invoice:
    invoice_number: str | None = None
    vendor_name: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    currency: str | None = "USD"
    line_items: list[LineItem] = field(default_factory=list)
    subtotal: float | None = None
    tax_amount: float | None = None
    shipping_amount: float | None = None
    total_amount: float | None = None
    payment_terms: str | None = None
    source_path: str | None = None
    source_format: str | None = None
    raw_text: str | None = None


@dataclass(slots=True)
class Finding:
    severity: str
    code: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class IngestionResult:
    invoice: Invoice
    findings: list[Finding] = field(default_factory=list)


@dataclass(slots=True)
class ValidationResult:
    findings: list[Finding] = field(default_factory=list)
    is_blocked: bool = False


@dataclass(slots=True)
class ApprovalResult:
    status: str
    rationale: str
    findings: list[Finding] = field(default_factory=list)


@dataclass(slots=True)
class PaymentResult:
    status: str
    message: str
    provider_response: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProcessingResult:
    status: str
    summary: str
    invoice: Invoice
    ingestion: IngestionResult
    validation: ValidationResult
    approval: ApprovalResult
    payment: PaymentResult | None = None
