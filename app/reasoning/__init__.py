from __future__ import annotations

from app.config import AppConfig
from app.reasoning.base import Reasoner
from app.reasoning.ollama import OllamaReasoner
from app.reasoning.rule_based import RuleBasedReasoner


def build_reasoner(config: AppConfig) -> Reasoner:
    if config.reasoner_backend == "ollama":
        return OllamaReasoner(
            model=config.ollama_model,
            base_url=config.ollama_base_url,
            fallback=RuleBasedReasoner(),
        )
    return RuleBasedReasoner()
