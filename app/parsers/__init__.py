from __future__ import annotations

from pathlib import Path

from app.parsers.base import BaseParser
from app.parsers.csv_parser import CsvInvoiceParser
from app.parsers.json_parser import JsonInvoiceParser
from app.parsers.pdf_parser import PdfInvoiceParser
from app.parsers.txt_parser import TextInvoiceParser
from app.parsers.xml_parser import XmlInvoiceParser


def get_parser_for_path(path: Path) -> BaseParser:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return JsonInvoiceParser()
    if suffix == ".csv":
        return CsvInvoiceParser()
    if suffix == ".txt":
        return TextInvoiceParser()
    if suffix == ".xml":
        return XmlInvoiceParser()
    if suffix == ".pdf":
        return PdfInvoiceParser()
    raise ValueError(f"Unsupported invoice format: {suffix}")
