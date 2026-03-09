from __future__ import annotations

import json
from urllib import error, request

from app.reasoning.base import (
    ApprovalDecisionContext,
    BorderlineTriageContext,
    CritiqueContext,
    ExceptionSummaryContext,
    IngestionAmbiguityContext,
    NoteRiskContext,
    RejectionSummaryContext,
)
from app.reasoning.rule_based import RuleBasedReasoner


class OllamaReasoner:
    def __init__(self, model: str, base_url: str, fallback: RuleBasedReasoner | None = None) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.fallback = fallback or RuleBasedReasoner()

    def build_rationale(self, context: ApprovalDecisionContext) -> str:
        prompt = self._build_rationale_prompt(context)
        return self._generate(prompt, lambda: self.fallback.build_rationale(context))

    def build_critique(self, context: CritiqueContext) -> str:
        prompt = self._build_critique_prompt(context)
        return self._generate(prompt, lambda: self.fallback.build_critique(context))

    def resolve_ambiguous_invoice(self, context: IngestionAmbiguityContext) -> dict[str, str]:
        prompt = self._build_ambiguity_prompt(context)
        return self._generate_json(
            prompt,
            lambda: self.fallback.resolve_ambiguous_invoice(context),
            {"vendor_name", "invoice_number", "due_date"},
        )

    def classify_note_risk(self, context: NoteRiskContext) -> str | None:
        prompt = self._build_note_risk_prompt(context)
        text = self._generate(prompt, lambda: self.fallback.classify_note_risk(context))
        normalized = text.strip()
        return normalized or None

    def summarize_rejection(self, context: RejectionSummaryContext) -> str:
        prompt = self._build_rejection_summary_prompt(context)
        return self._generate(prompt, lambda: self.fallback.summarize_rejection(context))

    def summarize_exceptions(self, context: ExceptionSummaryContext) -> str | None:
        prompt = self._build_exception_summary_prompt(context)
        text = self._generate(prompt, lambda: self.fallback.summarize_exceptions(context) or "")
        normalized = text.strip()
        return normalized or None

    def triage_borderline(self, context: BorderlineTriageContext) -> bool:
        prompt = self._build_borderline_triage_prompt(context)
        text = self._generate(prompt, lambda: "yes" if self.fallback.triage_borderline(context) else "no")
        return text.strip().lower().startswith("yes")

    def _generate(self, prompt: str, fallback) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=f"{self.base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            return fallback()

        text = str(body.get("response", "")).strip()
        return text or fallback()

    def _generate_json(self, prompt: str, fallback, allowed_keys: set[str]) -> dict[str, str]:
        raw_text = self._generate(prompt, lambda: json.dumps(fallback()))
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            return fallback()
        if not isinstance(parsed, dict):
            return fallback()

        result: dict[str, str] = {}
        for key, value in parsed.items():
            if key in allowed_keys and isinstance(value, str) and value.strip():
                result[key] = value.strip()
        return result

    def _build_rationale_prompt(self, context: ApprovalDecisionContext) -> str:
        finding_lines = "\n".join(
            f"- {finding.severity}:{finding.code} -> {finding.message}"
            for finding in context.decisive_findings
        ) or "- none"
        return (
            "You are an approval reviewer for invoice processing.\n"
            "Write a concise approval rationale in 1-2 sentences.\n"
            f"Decision: {context.decision}\n"
            f"Decision reason: {context.decision_reason}\n"
            f"Vendor: {context.invoice.vendor_name or 'UNKNOWN'}\n"
            f"Total amount: {context.invoice.total_amount}\n"
            "Decisive findings:\n"
            f"{finding_lines}\n"
            "Do not invent facts. Be concise."
        )

    def _build_critique_prompt(self, context: CritiqueContext) -> str:
        blocking_codes = ", ".join(f.code for f in context.blocking_findings) or "none"
        fraud_codes = ", ".join(f.code for f in context.fraud_findings) or "none"
        return (
            "You are critiquing an approval decision for invoice processing.\n"
            "Write a concise critique summary in 1 sentence.\n"
            f"Blocking validation findings: {blocking_codes}\n"
            f"Fraud findings: {fraud_codes}\n"
            "If both exist, say fraud should take precedence."
        )

    def _build_ambiguity_prompt(self, context: IngestionAmbiguityContext) -> str:
        invoice = context.invoice
        return (
            "You are helping extract missing invoice fields from messy unstructured text.\n"
            "Return ONLY JSON with any of these keys when you can infer them with confidence: "
            "vendor_name, invoice_number, due_date.\n"
            "If unsure, return an empty JSON object.\n"
            f"Existing vendor_name: {invoice.vendor_name}\n"
            f"Existing invoice_number: {invoice.invoice_number}\n"
            f"Existing due_date: {invoice.due_date}\n"
            "Raw text:\n"
            f"{invoice.raw_text or ''}\n"
        )

    def _build_note_risk_prompt(self, context: NoteRiskContext) -> str:
        tokens = ", ".join(context.heuristic_tokens) or "none"
        return (
            "You classify suspicious free-text invoice notes.\n"
            "Respond with one concise sentence describing risk signals, or return empty text if no risk.\n"
            f"Heuristic matched tokens: {tokens}\n"
            "Raw text:\n"
            f"{context.invoice.raw_text or ''}\n"
        )

    def _build_rejection_summary_prompt(self, context: RejectionSummaryContext) -> str:
        val_codes = ", ".join(f.code for f in context.validation_findings) or "none"
        appr_codes = ", ".join(f.code for f in context.approval_findings) or "none"
        return (
            "Summarize why this invoice was rejected for a human reviewer in 1-2 sentences.\n"
            f"Invoice number: {context.invoice.invoice_number or 'UNKNOWN'}\n"
            f"Vendor: {context.invoice.vendor_name or 'UNKNOWN'}\n"
            f"Validation finding codes: {val_codes}\n"
            f"Approval finding codes: {appr_codes}\n"
        )

    def _build_exception_summary_prompt(self, context: ExceptionSummaryContext) -> str:
        warning_lines = "\n".join(
            f"- {f.code}: {f.message}" for f in context.validation_findings if f.severity == "warning"
        ) or "- none"
        return (
            "Explain warning-level exceptions for a human reviewer in 1 sentence.\n"
            "If there are no warnings, return empty text.\n"
            "Warnings:\n"
            f"{warning_lines}\n"
        )

    def _build_borderline_triage_prompt(self, context: BorderlineTriageContext) -> str:
        warning_lines = "\n".join(
            f"- {f.code}: {f.message}" for f in context.validation_findings if f.severity == "warning"
        ) or "- none"
        return (
            "Decide if this invoice should be escalated to human review as borderline.\n"
            "Answer with YES or NO only.\n"
            f"Total amount: {context.invoice.total_amount}\n"
            "Warning findings:\n"
            f"{warning_lines}\n"
        )
