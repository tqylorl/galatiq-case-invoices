from __future__ import annotations

from datetime import datetime, UTC
from time import perf_counter
from uuid import uuid4

from app.agents.approval import ApprovalAgent
from app.agents.ingestion import IngestionAgent
from app.agents.payment import PaymentAgent
from app.agents.validation import ValidationAgent
from app.config import AppConfig
from app.models import PaymentResult, ProcessingEvent, ProcessingResult, StageMetric
from app.reasoning import build_reasoner


class InvoiceProcessor:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.reasoner = build_reasoner(config)
        self.ingestion_agent = IngestionAgent(self.reasoner)
        self.validation_agent = ValidationAgent(config.db_path, self.reasoner)
        self.approval_agent = ApprovalAgent(self.reasoner)
        self.payment_agent = PaymentAgent()

    def process(self) -> ProcessingResult:
        processing_id = str(uuid4())
        started_at = self._timestamp()
        events: list[ProcessingEvent] = [
            ProcessingEvent(
                timestamp=started_at,
                stage="pipeline",
                event="processing_started",
                details={"invoice_path": str(self.config.invoice_path)},
            )
        ]
        stage_metrics: list[StageMetric] = []

        ingestion, ingestion_metric = self._run_stage(
            "ingestion",
            lambda: self.ingestion_agent.run(self.config.invoice_path),
            lambda result: len(result.findings),
            events,
        )
        stage_metrics.append(ingestion_metric)

        validation, validation_metric = self._run_stage(
            "validation",
            lambda: self.validation_agent.run(ingestion.invoice),
            lambda result: len(result.findings),
            events,
        )
        stage_metrics.append(validation_metric)

        approval, approval_metric = self._run_stage(
            "approval",
            lambda: self.approval_agent.run(ingestion.invoice, validation),
            lambda result: len(result.findings),
            events,
        )
        stage_metrics.append(approval_metric)

        payment: PaymentResult | None = None
        if approval.status == "approved":
            payment, payment_metric = self._run_stage(
                "payment",
                lambda: self.payment_agent.run(ingestion.invoice),
                lambda result: 0,
                events,
            )
            stage_metrics.append(payment_metric)
        else:
            events.append(
                ProcessingEvent(
                    timestamp=self._timestamp(),
                    stage="payment",
                    event="skipped",
                    details={"approval_status": approval.status},
                )
            )

        summary = approval.rationale if payment is None else payment.message
        completed_at = self._timestamp()
        events.append(
            ProcessingEvent(
                timestamp=completed_at,
                stage="pipeline",
                event="processing_completed",
                details={"status": approval.status},
            )
        )
        return ProcessingResult(
            processing_id=processing_id,
            started_at=started_at,
            completed_at=completed_at,
            status=approval.status,
            summary=summary,
            invoice=ingestion.invoice,
            ingestion=ingestion,
            validation=validation,
            approval=approval,
            payment=payment,
            stage_metrics=stage_metrics,
            events=events,
        )

    def _run_stage(self, stage: str, fn, finding_count_fn, events: list[ProcessingEvent]):
        start_timestamp = self._timestamp()
        events.append(ProcessingEvent(timestamp=start_timestamp, stage=stage, event="started"))
        start = perf_counter()
        result = fn()
        duration_ms = round((perf_counter() - start) * 1000, 3)
        status = getattr(result, "status", "completed")
        finding_count = finding_count_fn(result)
        events.append(
            ProcessingEvent(
                timestamp=self._timestamp(),
                stage=stage,
                event="completed",
                details={
                    "status": status,
                    "duration_ms": duration_ms,
                    "finding_count": finding_count,
                },
            )
        )
        return result, StageMetric(
            stage=stage,
            status=status,
            duration_ms=duration_ms,
            finding_count=finding_count,
        )

    def _timestamp(self) -> str:
        return datetime.now(UTC).isoformat()
