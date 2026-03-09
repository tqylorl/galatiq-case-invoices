from __future__ import annotations

import json
from io import BytesIO
from urllib import error

from app.agents.approval import ApprovalAgent
from app.models import Finding, Invoice, ValidationResult
from app.reasoning.base import ApprovalDecisionContext, CritiqueContext
from app.reasoning.ollama import OllamaReasoner
from app.reasoning.rule_based import RuleBasedReasoner


class FakeResponse:
    def __init__(self, payload: dict[str, str]) -> None:
        self.payload = BytesIO(json.dumps(payload).encode("utf-8"))

    def read(self) -> bytes:
        return self.payload.read()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def make_invoice(total_amount: float | None = 1000.0) -> Invoice:
    return Invoice(vendor_name="Precision Parts Ltd.", due_date="2026-02-22", total_amount=total_amount)


def test_rule_based_reasoner_builds_pending_review_rationale() -> None:
    reasoner = RuleBasedReasoner()

    rationale = reasoner.build_rationale(
        ApprovalDecisionContext(
            invoice=make_invoice(total_amount=15225.0),
            validation=ValidationResult(),
            decision="pending_review",
            decision_reason="scrutiny_threshold",
            decisive_findings=[],
        )
    )

    assert "exceeds the 10000.00 threshold" in rationale


def test_ollama_reasoner_uses_remote_response(monkeypatch) -> None:
    def fake_urlopen(req, timeout=20):
        return FakeResponse({"response": "LLM rationale"})

    monkeypatch.setattr("app.reasoning.ollama.request.urlopen", fake_urlopen)
    reasoner = OllamaReasoner("qwen2.5:7b", "http://localhost:11434")

    rationale = reasoner.build_rationale(
        ApprovalDecisionContext(
            invoice=make_invoice(),
            validation=ValidationResult(),
            decision="approved",
            decision_reason="clear",
            decisive_findings=[],
        )
    )

    assert rationale == "LLM rationale"


def test_ollama_reasoner_falls_back_when_request_fails(monkeypatch) -> None:
    def fake_urlopen(req, timeout=20):
        raise error.URLError("offline")

    monkeypatch.setattr("app.reasoning.ollama.request.urlopen", fake_urlopen)
    reasoner = OllamaReasoner("qwen2.5:7b", "http://localhost:11434")

    rationale = reasoner.build_rationale(
        ApprovalDecisionContext(
            invoice=make_invoice(),
            validation=ValidationResult(
                findings=[Finding("error", "unknown_item", "Item was not found.")]
            ),
            decision="rejected",
            decision_reason="validation_errors",
            decisive_findings=[Finding("error", "unknown_item", "Item was not found.")],
        )
    )

    assert "blocking validation errors" in rationale.lower()


def test_approval_agent_uses_reasoner_for_rationale_and_critique() -> None:
    class StubReasoner:
        def build_rationale(self, context):
            return f"stub rationale for {context.decision}"

        def build_critique(self, context):
            return "stub critique"

    agent = ApprovalAgent(StubReasoner())
    validation = ValidationResult(
        findings=[Finding("error", "unknown_item", "Item was not found.")],
        is_blocked=True,
    )

    result = agent.run(make_invoice(), validation)

    assert result.rationale == "stub rationale for rejected"
    assert any(finding.message == "stub critique" for finding in result.findings)
