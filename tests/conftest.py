from __future__ import annotations

from pathlib import Path

import pytest

from app.config import AppConfig
from app.db import bootstrap_inventory_db
from app.orchestrator import InvoiceProcessor


REPO_ROOT = Path(__file__).resolve().parents[1]
INVOICES_DIR = REPO_ROOT / "data" / "invoices"


@pytest.fixture
def invoices_dir() -> Path:
    return INVOICES_DIR


@pytest.fixture
def seeded_db_path(tmp_path: Path) -> Path:
    db_path = tmp_path / "inventory.db"
    bootstrap_inventory_db(db_path)
    return db_path


@pytest.fixture
def run_invoice(seeded_db_path: Path):
    def _run_invoice(invoice_name: str):
        config = AppConfig(
            invoice_path=INVOICES_DIR / invoice_name,
            db_path=seeded_db_path,
            output_format="json",
        )
        processor = InvoiceProcessor(config)
        return processor.process()

    return _run_invoice
