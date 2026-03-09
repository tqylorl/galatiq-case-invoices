# Invoice Automation Roadmap

## Current State

The prototype now supports a full local workflow for invoice processing:

- Multi-format ingestion for `.txt`, `.json`, `.csv`, `.xml`, and `.pdf`
- SQLite-backed validation with stock, totals, date, and fraud checks
- Deterministic approval decisions with optional Ollama-backed reasoning
- Mock payment execution for approved invoices
- Batch processing with per-invoice JSON reports and batch summary export
- Parser, validation, approval, reasoning, pipeline, and CLI test coverage

## Implemented Capabilities

### Ingestion

- Format-aware parsers normalize all supported invoice inputs into a canonical `Invoice` model.
- TXT and PDF handling support messy unstructured invoices, OCR-like cleanup, and PDF text extraction.
- Ambiguous TXT/PDF invoices can use the configured reasoner to fill missing `vendor_name`, `invoice_number`, and `due_date`.

### Validation

- Checks inventory existence, zero-stock items, insufficient stock, negative quantities, and negative totals.
- Reconciles subtotal and total amounts against line items, tax, and shipping.
- Flags suspicious relative dates and urgent free-text payment language.
- Supports LLM-assisted note-risk classification through the reasoner layer.

### Approval and Payment

- Deterministic approval rules decide `approved`, `rejected`, or `pending_review`.
- Approval generates critique, rejection summaries, exception summaries, and borderline review triage.
- Ollama can be used to enrich rationale, critique, exception handling, and ambiguity resolution while rule-based logic remains the guardrail.
- Approved invoices call the mock payment agent.

### Reporting and Batch Mode

- Single-invoice mode can optionally write a JSON report.
- Batch mode processes all supported invoice files in a directory.
- Batch runs export:
  - one JSON result per invoice
  - one `batch_summary.json` file with totals and statuses

## CLI Usage

Run a single invoice:

```bash
python3 main.py --invoice_path data/invoices/invoice_1004.json --db-path inventory.db --bootstrap-db --output json
```

Run a directory of invoices:

```bash
python3 main.py --invoice_dir data/invoices --db-path inventory.db --bootstrap-db --report-dir reports --output text
```

Run with Ollama reasoning:

```bash
python3 main.py \
  --invoice_path data/invoices/invoice_1003.txt \
  --db-path inventory.db \
  --bootstrap-db \
  --reasoner ollama \
  --ollama-model qwen2.5:7b \
  --ollama-base-url http://localhost:11434 \
  --output json
```

## Supported Arguments

- `--invoice_path`
  Process one invoice file.
- `--invoice_dir`
  Process all supported invoice files in a directory.
- `--db-path`
  Path to the SQLite inventory database. Default: `inventory.db`
- `--output`
  Output format: `json` or `text`. Default: `json`
- `--bootstrap-db`
  Create and seed the inventory database before processing.
- `--reasoner`
  Reasoning backend: `rule` or `ollama`. Default: `rule`
- `--ollama-model`
  Ollama model name when using `--reasoner ollama`. Default: `qwen2.5:7b`
- `--ollama-base-url`
  Base URL for the local Ollama server. Default: `http://localhost:11434`
- `--report-dir`
  Directory for JSON reports. Optional in single-file mode. Defaults to `reports/` in batch mode.

## Near-Term Next Steps

- Add duplicate invoice detection and vendor policy checks.
- Improve reviewer-facing outputs beyond raw JSON, such as a cleaner review summary.
- Add stronger Ollama prompt hardening and output validation if the LLM becomes more central to reviewer workflows.
- Extend batch reporting with top rejection reasons and fraud metrics.

## Guardrails and LLM Design Rationale

This system intentionally uses deterministic guardrails for payment-critical decisions and probabilistic reasoning for ambiguous or reviewer-facing tasks.

- Deterministic guardrails:
  inventory checks, quantity checks, total reconciliation, approval status gating, and payment execution are all enforced by explicit code paths.
- Probabilistic guardrails:
  the LLM is used to assist with ambiguous extraction, suspicious note classification, rejection summaries, exception summaries, critique narratives, and borderline triage support.

The project does not use the LLM as the core decision engine because invoice processing is an operational workflow that benefits from repeatability, auditability, and predictable failure modes. In a production-style design, stock validation, approval gating, and payment authorization should remain deterministic, while the LLM adds value where interpretation, explanation, or ambiguity resolution is needed. This approach still satisfies the agentic goals of the prototype while keeping unsafe model behavior from directly authorizing payments or overriding hard validation rules.
