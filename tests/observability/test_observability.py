from __future__ import annotations

import json
from pathlib import Path

from app.cli import process_single_invoice
from app.config import AppConfig


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_processing_result_contains_stage_metrics_and_events(seeded_db_path: Path) -> None:
    config = AppConfig(
        invoice_path=REPO_ROOT / "data" / "invoices" / "invoice_1004.json",
        db_path=seeded_db_path,
        output_format="json",
    )

    result = process_single_invoice(config)

    assert result.processing_id
    assert result.started_at
    assert result.completed_at
    assert [metric.stage for metric in result.stage_metrics] == [
        "ingestion",
        "validation",
        "approval",
        "payment",
    ]
    assert any(event.event == "processing_started" for event in result.events)
    assert any(event.stage == "payment" and event.event == "completed" for event in result.events)


def test_single_invoice_report_includes_observability_metadata(
    tmp_path: Path,
    seeded_db_path: Path,
) -> None:
    from app.cli import write_single_report

    config = AppConfig(
        invoice_path=REPO_ROOT / "data" / "invoices" / "invoice_1004.json",
        db_path=seeded_db_path,
        output_format="json",
    )
    result = process_single_invoice(config)

    report_path = write_single_report(tmp_path, config.invoice_path, result)
    payload = json.loads(report_path.read_text())

    assert payload["processing_id"]
    assert payload["stage_metrics"]
    assert payload["events"]
