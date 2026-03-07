from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    invoice_path: Path
    db_path: Path
    output_format: str = "json"
