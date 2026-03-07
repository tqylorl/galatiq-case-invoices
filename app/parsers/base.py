from __future__ import annotations

from pathlib import Path

from app.models import Invoice


class BaseParser:
    def parse(self, invoice_path: Path) -> Invoice:
        raise NotImplementedError
