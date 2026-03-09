from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import cli


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_discover_invoice_files_filters_supported_extensions(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text("{}")
    (tmp_path / "b.txt").write_text("INVOICE")
    (tmp_path / "c.md").write_text("# note")
    (tmp_path / "d.pdf").write_bytes(b"%PDF-1.4")

    discovered = cli.discover_invoice_files(tmp_path)

    assert [path.name for path in discovered] == ["a.json", "b.txt", "d.pdf"]


def test_batch_main_writes_reports_and_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    invoice_dir = tmp_path / "invoices"
    invoice_dir.mkdir()
    report_dir = tmp_path / "reports"
    db_path = tmp_path / "inventory.db"

    (invoice_dir / "invoice_1004.json").write_text(
        (REPO_ROOT / "data" / "invoices" / "invoice_1004.json").read_text()
    )
    (invoice_dir / "invoice_1002.txt").write_text(
        (REPO_ROOT / "data" / "invoices" / "invoice_1002.txt").read_text()
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "main.py",
            "--invoice_dir",
            str(invoice_dir),
            "--db-path",
            str(db_path),
            "--bootstrap-db",
            "--report-dir",
            str(report_dir),
            "--output",
            "json",
        ],
    )

    exit_code = cli.main()

    # One invoice is expected to reject, so batch exit code should be non-zero.
    assert exit_code == 1

    invoice_report_files = sorted(path.name for path in report_dir.glob("*_result.json"))
    assert invoice_report_files == ["invoice_1002_result.json", "invoice_1004_result.json"]

    summary = json.loads((report_dir / "batch_summary.json").read_text())
    assert summary["total_invoices"] == 2
    assert summary["status_counts"]["approved"] == 1
    assert summary["status_counts"]["rejected"] == 1
