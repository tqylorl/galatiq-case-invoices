from __future__ import annotations

import sqlite3
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
    def _run_invoice(invoice_name: str, *, db_path: Path | None = None):
        config = AppConfig(
            invoice_path=INVOICES_DIR / invoice_name,
            db_path=db_path or seeded_db_path,
            output_format="json",
        )
        processor = InvoiceProcessor(config)
        return processor.process()

    return _run_invoice


@pytest.fixture
def set_inventory_stock(seeded_db_path: Path):
    def _set_inventory_stock(item_name: str, stock: int) -> None:
        connection = sqlite3.connect(seeded_db_path)
        try:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO inventory (item, stock) VALUES (?, ?)",
                (item_name, stock),
            )
            connection.commit()
        finally:
            connection.close()

    return _set_inventory_stock
