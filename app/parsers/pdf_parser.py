from __future__ import annotations

from pathlib import Path

from app.models import Invoice
from app.parsers.base import BaseParser
from app.parsers.txt_parser import TextInvoiceParser


class PdfInvoiceParser(BaseParser):
    def parse(self, invoice_path: Path) -> Invoice:
        try:
            import pypdf
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "PDF parsing requires the 'pypdf' package. Install it before processing PDFs."
            ) from exc

        reader = pypdf.PdfReader(str(invoice_path))
        extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)

        temp_path = invoice_path.with_suffix(".txt")
        parser = TextInvoiceParser()
        invoice = parser.parse(temp_path) if temp_path.exists() else Invoice(raw_text=extracted_text)
        if not temp_path.exists():
            invoice.raw_text = extracted_text
        return invoice
