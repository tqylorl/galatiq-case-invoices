from __future__ import annotations

import json
from urllib import error, request

from app.reasoning.base import ApprovalDecisionContext, CritiqueContext
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
