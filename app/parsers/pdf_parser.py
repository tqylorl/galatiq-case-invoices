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

        parser = TextInvoiceParser()
        return parser.parse_text(extracted_text)
