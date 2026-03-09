from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    invoice_path: Path
    db_path: Path
    output_format: str = "json"
    reasoner_backend: str = "rule"
    ollama_model: str = "qwen2.5:7b"
    ollama_base_url: str = "http://localhost:11434"
