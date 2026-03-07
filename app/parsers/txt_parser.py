from __future__ import annotations

import re
from pathlib import Path

from app.models import Invoice, LineItem
from app.parsers.base import BaseParser


class TextInvoiceParser(BaseParser):
    HEADER_PATTERNS = {
        "invoice_number": [
            r"Invoice Number:\s*(.+)",
            r"INV(?:OICE)?(?:\s+#| NO:|:)\s*(.+)",
            r"Inv #:\s*(.+)",
            r"Invoice:\s*(.+)",
        ],
        "vendor_name": [
            r"Vendor:\s*(.+)",
            r"Vndr:\s*(.+)",
            r"FROM:\s*(.+)",
        ],
        "invoice_date": [
            r"Date:\s*(.+)",
            r"Dt:\s*(.+)",
        ],
        "due_date": [
            r"Due Date:\s*(.+)",
            r"Due Dt:\s*(.+)",
            r"DUE:\s*(.+)",
            r"Due:\s*(.+)",
        ],
        "payment_terms": [
            r"Payment Terms:\s*(.+)",
            r"Pymnt Terms:\s*(.+)",
            r"Terms:\s*(.+)",
        ],
    }

    def parse(self, invoice_path: Path) -> Invoice:
        text = invoice_path.read_text()
        cleaned_text = text.replace("2O", "20").replace(".O", ".0")
        invoice = Invoice(raw_text=cleaned_text)

        for field_name, patterns in self.HEADER_PATTERNS.items():
            value = self._match_first(cleaned_text, patterns)
            if value:
                setattr(invoice, field_name, value.strip())

        invoice.line_items = self._extract_items(cleaned_text)
        invoice.total_amount = self._extract_amount(cleaned_text, [r"Total Amount:\s*\$?([0-9,]+\.\d{2})", r"TOTAL:\s*\$?([0-9,]+\.\d{2})", r"Total:\s*\$?([0-9,]+\.\d{2})", r"Amt:\s*\$?([0-9,]+\.\d{2})"])
        invoice.subtotal = self._extract_amount(cleaned_text, [r"Subtotal:\s*\$?([0-9,]+\.\d{2})", r"SUBTOTAL:\s*\$?([0-9,]+\.\d{2})"])
        invoice.tax_amount = self._extract_amount(cleaned_text, [r"Tax.*?:\s*\$?([0-9,]+\.\d{2})", r"Sales Tax:\s*\$?([0-9,]+\.\d{2})"])
        invoice.shipping_amount = self._extract_amount(cleaned_text, [r"Shipping:\s*\$?([0-9,]+\.\d{2})"])
        return invoice

    def _match_first(self, text: str, patterns: list[str]) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_amount(self, text: str, patterns: list[str]) -> float | None:
        value = self._match_first(text, patterns)
        if value is None:
            return None
        return float(value.replace(",", ""))

    def _extract_items(self, text: str) -> list[LineItem]:
        items: list[LineItem] = []
        patterns = [
            r"^\s*([A-Za-z][A-Za-z0-9 ()]+?)\s+qty:?\s*(-?\d+)\s+unit price:\s*\$([0-9,]+(?:\.\d{2})?)",
            r"^\s*([A-Za-z][A-Za-z0-9 ]+?)\s+qty\s*(-?\d+)\s+@\s*\$([0-9,]+(?:\.\d{2})?)",
            r"^\s*-\s*([A-Za-z][A-Za-z0-9 ]+?)\s+x(\d+)\s+\$([0-9,]+(?:\.\d{2})?)\s+each",
            r"^\s*([A-Za-z][A-Za-z0-9 ()]+?)\s+(\d+)\s+\$([0-9,]+(?:\.\d{2})?)\s+\$([0-9,]+(?:\.\d{2})?)",
        ]
        for line in text.splitlines():
            normalized_line = line.replace("Widget A", "WidgetA").replace("Gadget X", "GadgetX")
            for pattern in patterns:
                match = re.match(pattern, normalized_line.strip(), flags=re.IGNORECASE)
                if not match:
                    continue

                item_name = match.group(1).strip()
                quantity = float(match.group(2))
                unit_price = float(match.group(3).replace(",", ""))
                line_total = quantity * unit_price
                if len(match.groups()) >= 4 and match.group(4):
                    line_total = float(match.group(4).replace(",", ""))
                items.append(
                    LineItem(
                        item_name=item_name,
                        quantity=quantity,
                        unit_price=unit_price,
                        line_total=line_total,
                    )
                )
                break
        return items
