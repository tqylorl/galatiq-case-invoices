from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.config import AppConfig
from app.db import bootstrap_inventory_db
from app.orchestrator import InvoiceProcessor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process a single invoice file.")
    parser.add_argument("--invoice_path", required=True, help="Path to the invoice file.")
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
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = AppConfig(
        invoice_path=Path(args.invoice_path),
        db_path=Path(args.db_path),
        output_format=args.output,
        reasoner_backend=args.reasoner,
        ollama_model=args.ollama_model,
        ollama_base_url=args.ollama_base_url,
    )

    if args.bootstrap_db:
        bootstrap_inventory_db(config.db_path)

    processor = InvoiceProcessor(config)
    result = processor.process()

    if config.output_format == "json":
        print(json.dumps(asdict(result), indent=2, default=str))
    else:
        print(result.status)
        print(result.summary)

    return 0 if result.status == "approved" else 1
