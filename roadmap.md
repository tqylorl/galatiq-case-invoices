# Invoice Automation MVP Plan

## Summary

Build a Python CLI prototype that processes one invoice at a time through four explicit agents: ingestion, validation, approval, and payment. Optimize for a shippable MVP using a custom orchestration layer instead of a heavy agent framework, but keep the design clearly multi-agent by giving each stage its own interface, structured input/output contract, and audit trail.

The system should support the provided formats (`.txt`, `.json`, `.csv`, `.xml`, `.pdf`), normalize them into one canonical invoice schema, validate against a local SQLite `inventory.db`, run a rule-based approval agent with a critique/reflection pass, and either call a mock payment function or log a rejection with reasons.

## Key Changes

### Architecture and flow

- Add a `main.py` CLI entrypoint: `python main.py --invoice_path=... [--output=json|text] [--db-path=inventory.db]`.
- Add a lightweight orchestrator that runs stages in order and stops on hard failures:
  1. ingestion
  2. validation
  3. approval
  4. payment
- Persist a structured per-run result object containing:
  - normalized invoice data
  - extraction warnings
  - validation findings
  - approval decision and rationale
  - payment result or rejection log

### Core interfaces / types

- Define a canonical `Invoice` model with:
  - `invoice_number`
  - `vendor_name`
  - `invoice_date`
  - `due_date`
  - `currency`
  - `line_items[]` with `item_name`, `quantity`, `unit_price`, `line_total`, `notes`
  - `subtotal`, `tax_amount`, `shipping_amount`, `total_amount`
  - `payment_terms`
  - `source_path`, `source_format`
- Define stage result models:
  - `IngestionResult`
  - `ValidationResult`
  - `ApprovalResult`
  - `PaymentResult`
  - `ProcessingResult`
- Standardize finding severity levels: `info`, `warning`, `error`, `fraud_risk`.

### Ingestion agent

- Route by file extension to format-specific parsers:
  - `.json`: direct structured parse with field normalization
  - `.csv`: support both key/value CSV and row-per-line-item CSV
  - `.xml`: parse header, items, totals
  - `.txt` / extracted PDF text: heuristic parser for messy labels and table-like rows
  - `.pdf`: extract text first, then reuse the text parser
- Implement normalization rules needed by the provided samples:
  - common OCR cleanup (`2O26` -> `2026`, `O0` -> `00`)
  - label synonym mapping (`Vndr`, `Inv #`, `Due Dt`, etc.)
  - item synonym mapping (`Widget A` -> `WidgetA`, `Gadget X` -> `GadgetX`)
  - date parsing for ISO, `Jan 30 2026`, `26-Jan-2026`, `January 27, 2026`
- Flag but do not silently discard bad data:
  - missing vendor
  - null/missing due date
  - negative quantities
  - inconsistent totals
  - suspicious relative dates like `yesterday`

### Validation agent

- Add a DB bootstrap script that creates `inventory.db` and seeds at least the README’s required inventory rows.
- Validate:
  - item exists in inventory
  - quantity is positive
  - requested quantity does not exceed stock
  - invoice totals roughly reconcile from line items, tax, and shipping when enough data exists
- Mark suspicious cases clearly:
  - zero-stock items
  - unknown items
  - malformed vendor/date fields
  - large amount + urgent payment language
- Validation output should separate:
  - blocking errors
  - non-blocking warnings
  - fraud-risk indicators

### Approval and payment agents

- Approval agent uses deterministic business rules first:
  - auto-reject on blocking validation errors
  - escalate or require extra scrutiny for totals over `$10,000`
  - reject invoices with strong fraud indicators
- Add a simple critique/reflection pass:
  - first pass produces decision + rationale
  - second pass checks for missed blocking issues or contradictions
  - final decision is emitted only after critique resolves
- Payment agent only runs on approved invoices and calls the provided mock payment function.
- Rejected invoices should still produce a complete final report with explicit reasons.

## Test Plan

- Parse and process clean invoices successfully:
  - `invoice_1001.txt`
  - `invoice_1004.json`
  - `invoice_1006.csv`
  - `invoice_1014.xml`
- Catch inventory and integrity failures:
  - `invoice_1002.txt` quantity exceeds stock
  - `invoice_1003.txt` zero-stock fraudulent item
  - `invoice_1008.txt` unknown items
  - `invoice_1009.json` negative quantity and missing fields
  - `invoice_1016.json` unknown `WidgetC`
- Verify messy-ingestion behavior:
  - `invoice_1012.txt` / `invoice_1012.pdf` OCR-style cleanup
  - `invoice_1010.txt` repeated item names plus shipping
  - `invoice_1015.csv` row-style line items plus totals footer
- Verify approval behavior:
  - invoices over `$10,000` trigger scrutiny
  - blocking validation errors prevent payment
  - approved invoices call payment exactly once
- Add at least one CLI-level integration test that processes a file end-to-end and asserts the final status payload.

## Assumptions

- Target UX is CLI-only for this prototype.
- Use a custom Python multi-agent pipeline rather than LangGraph/CrewAI to reduce delivery risk.
- Grok/xAI integration should be designed as a pluggable adapter, but the MVP must run locally without requiring an API key; deterministic logic and optional LLM hooks are sufficient for the first implementation.
- SQLite inventory validation is file-local and single-user; no concurrency or external service concerns need to be solved in v1.
- PDF handling can rely on text extraction only; scanned-image OCR beyond the provided samples is out of scope for the MVP.
