from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from app.config import AppConfig
from app.db import bootstrap_inventory_db
from app.models import ProcessingResult
from app.orchestrator import InvoiceProcessor

SUPPORTED_INVOICE_EXTENSIONS = {".txt", ".json", ".csv", ".xml", ".pdf"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process invoice files.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--invoice_path", help="Path to a single invoice file.")
    input_group.add_argument("--invoice_dir", help="Path to a directory of invoice files.")
    parser.add_argument(
        "--db-path",
        default="inventory.db",
        help="Path to the SQLite inventory database.",
    )
    parser.add_argument(
        "--output",
        choices=("json", "text"),
        default="json",
        help="Output format for the processing result.",
    )
    parser.add_argument(
        "--bootstrap-db",
        action="store_true",
        help="Create the inventory database with seed data before processing.",
    )
    parser.add_argument(
        "--reasoner",
        choices=("rule", "ollama"),
        default="rule",
        help="Reasoning backend for approval rationale and critique.",
    )
    parser.add_argument(
        "--ollama-model",
        default="qwen2.5:7b",
        help="Ollama model name to use when --reasoner=ollama.",
    )
    parser.add_argument(
        "--ollama-base-url",
        default="http://localhost:11434",
        help="Base URL for the local Ollama server.",
    )
    parser.add_argument(
        "--report-dir",
        default=None,
        help="Directory to write JSON processing reports. Batch mode defaults to reports/ if omitted.",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Print per-stage execution trace to stderr.",
    )
    return parser


def discover_invoice_files(invoice_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in invoice_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_INVOICE_EXTENSIONS
    )


def process_single_invoice(config: AppConfig) -> ProcessingResult:
    processor = InvoiceProcessor(config)
    return processor.process()


def emit_trace(result: ProcessingResult) -> None:
    print(
        f"[trace] processing_id={result.processing_id} status={result.status} started_at={result.started_at}",
        file=sys.stderr,
    )
    for metric in result.stage_metrics:
        print(
            f"[trace] stage={metric.stage} status={metric.status} duration_ms={metric.duration_ms} findings={metric.finding_count}",
            file=sys.stderr,
        )


def write_single_report(report_dir: Path, invoice_path: Path, result: ProcessingResult) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{invoice_path.stem}_result.json"
    report_path.write_text(json.dumps(asdict(result), indent=2, default=str))
    return report_path


def write_batch_summary(
    report_dir: Path,
    results: list[tuple[Path, ProcessingResult]],
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    status_counts: dict[str, int] = {"approved": 0, "rejected": 0, "pending_review": 0}
    for _, result in results:
        status_counts[result.status] = status_counts.get(result.status, 0) + 1

    summary = {
        "total_invoices": len(results),
        "status_counts": status_counts,
        "invoices": [
            {
                "invoice_path": str(invoice_path),
                "status": result.status,
                "summary": result.summary,
            }
            for invoice_path, result in results
        ],
    }
    summary_path = report_dir / "batch_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    return summary_path


def main() -> int:
    args = build_parser().parse_args()
    db_path = Path(args.db_path)
    if args.bootstrap_db:
        bootstrap_inventory_db(db_path)

    if args.invoice_path:
        invoice_path = Path(args.invoice_path)
        config = AppConfig(
            invoice_path=invoice_path,
            db_path=db_path,
            output_format=args.output,
            reasoner_backend=args.reasoner,
            ollama_model=args.ollama_model,
            ollama_base_url=args.ollama_base_url,
            trace=args.trace,
        )
        result = process_single_invoice(config)
        if args.trace:
            emit_trace(result)
        if args.report_dir:
            write_single_report(Path(args.report_dir), invoice_path, result)

        if config.output_format == "json":
            print(json.dumps(asdict(result), indent=2, default=str))
        else:
            print(result.status)
            print(result.summary)

        return 0 if result.status == "approved" else 1

    invoice_dir = Path(args.invoice_dir)
    invoice_files = discover_invoice_files(invoice_dir)
    run_results: list[tuple[Path, ProcessingResult]] = []
    for invoice_path in invoice_files:
        config = AppConfig(
            invoice_path=invoice_path,
            db_path=db_path,
            output_format=args.output,
            reasoner_backend=args.reasoner,
            ollama_model=args.ollama_model,
            ollama_base_url=args.ollama_base_url,
            trace=args.trace,
        )
        result = process_single_invoice(config)
        if args.trace:
            emit_trace(result)
        run_results.append((invoice_path, result))

    report_dir = Path(args.report_dir) if args.report_dir else Path("reports")
    for invoice_path, result in run_results:
        write_single_report(report_dir, invoice_path, result)
    summary_path = write_batch_summary(report_dir, run_results)

    if args.output == "json":
        summary_payload = {
            "report_dir": str(report_dir),
            "summary_path": str(summary_path),
            "total_invoices": len(run_results),
            "status_counts": {
                "approved": sum(1 for _, result in run_results if result.status == "approved"),
                "rejected": sum(1 for _, result in run_results if result.status == "rejected"),
                "pending_review": sum(1 for _, result in run_results if result.status == "pending_review"),
            },
        }
        print(json.dumps(summary_payload, indent=2))
    else:
        approved = sum(1 for _, result in run_results if result.status == "approved")
        rejected = sum(1 for _, result in run_results if result.status == "rejected")
        pending = sum(1 for _, result in run_results if result.status == "pending_review")
        print(f"Processed {len(run_results)} invoices")
        print(f"approved={approved} rejected={rejected} pending_review={pending}")
        print(f"reports={report_dir}")

    return 0 if all(result.status == "approved" for _, result in run_results) else 1
