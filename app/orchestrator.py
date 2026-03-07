from __future__ import annotations

from app.agents.approval import ApprovalAgent
from app.agents.ingestion import IngestionAgent
from app.agents.payment import PaymentAgent
from app.agents.validation import ValidationAgent
from app.config import AppConfig
from app.models import PaymentResult, ProcessingResult


class InvoiceProcessor:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.ingestion_agent = IngestionAgent()
        self.validation_agent = ValidationAgent(config.db_path)
        self.approval_agent = ApprovalAgent()
        self.payment_agent = PaymentAgent()

    def process(self) -> ProcessingResult:
        ingestion = self.ingestion_agent.run(self.config.invoice_path)
        validation = self.validation_agent.run(ingestion.invoice)
        approval = self.approval_agent.run(ingestion.invoice, validation)

        payment: PaymentResult | None = None
        if approval.status == "approved":
            payment = self.payment_agent.run(ingestion.invoice)

        summary = approval.rationale if payment is None else payment.message
        return ProcessingResult(
            status=approval.status,
            summary=summary,
            invoice=ingestion.invoice,
            ingestion=ingestion,
            validation=validation,
            approval=approval,
            payment=payment,
        )
