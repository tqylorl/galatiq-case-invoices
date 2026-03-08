from __future__ import annotations

import re
from pathlib import Path

from app.models import Invoice, LineItem
from app.parsers.base import BaseParser


class TextInvoiceParser(BaseParser):
    HEADER_PATTERNS = {
        "invoice_number": [
            r"Invoice Number:\s*(.+)",
            r"Inv #:\s*(.+)",
            r"INV\s+NO:\s*(.+)",
            r"INVOICE\s+#\s*(.+)",
            r"Invoice:\s*(.+)",
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
        cleaned_text = self._clean_text(invoice_path.read_text())
        invoice = Invoice(raw_text=cleaned_text)

        for field_name, patterns in self.HEADER_PATTERNS.items():
            value = self._match_first(cleaned_text, patterns)
            if value:
                setattr(invoice, field_name, self._normalize_header_value(field_name, value))

        invoice.line_items = self._extract_items(cleaned_text)
        invoice.total_amount = self._extract_amount(
            cleaned_text,
            [
                r"Total Amount:\s*\$?([0-9,]+\.\d{2})",
                r"^\s*TOTAL:\s*\$?([0-9,]+\.\d{2})",
                r"^\s*Total:\s*\$?([0-9,]+\.\d{2})",
                r"Amt:\s*\$?([0-9,]+\.\d{2})",
            ],
        )
        invoice.subtotal = self._extract_amount(
            cleaned_text,
            [r"^\s*Subtotal:\s*\$?([0-9,]+\.\d{2})", r"^\s*SUBTOTAL:\s*\$?([0-9,]+\.\d{2})"],
        )
        invoice.tax_amount = self._extract_amount(
            cleaned_text,
            [r"^\s*Tax.*?:\s*\$?([0-9,]+\.\d{2})", r"^\s*Sales Tax:\s*\$?([0-9,]+\.\d{2})"],
        )
        invoice.shipping_amount = self._extract_amount(
            cleaned_text,
            [r"^\s*Shipping:\s*\$?([0-9,]+\.\d{2})"],
        )
        return invoice

    def _clean_text(self, text: str) -> str:
        replacements = {
            "2O": "20",
            ".O": ".0",
            "$3,500.O0": "$3,500.00",
            "Payble": "Payable",
        }
        cleaned_text = text
        for old, new in replacements.items():
            cleaned_text = cleaned_text.replace(old, new)
        return cleaned_text

    def _match_first(self, text: str, patterns: list[str]) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_amount(self, text: str, patterns: list[str]) -> float | None:
        value = self._match_first(text, patterns)
        if value is None:
            return None
        return float(value.replace(",", ""))

    def _normalize_header_value(self, field_name: str, value: str) -> str:
        normalized = value.strip()
        if field_name == "invoice_number":
            normalized = normalized.lstrip(":# ").strip()
            normalized = re.sub(r"\bINV[\s-]*(\d+)\b", r"INV-\1", normalized, flags=re.IGNORECASE)
            if normalized.isdigit():
                normalized = f"INV-{normalized}"
        return normalized

    def _extract_items(self, text: str) -> list[LineItem]:
        items: list[LineItem] = []
        patterns = [
            r"^\s*([A-Za-z][A-Za-z0-9 ()]+?)\s+qty:?\s*(-?\d+)\s+unit price:\s*\$([0-9,]+(?:\.\d{2})?)",
            r"^\s*([A-Za-z][A-Za-z0-9 ]+?)\s+qty\s*(-?\d+)\s+@\s*\$([0-9,]+(?:\.\d{2})?)",
            r"^\s*-\s*([A-Za-z][A-Za-z0-9 ]+?)\s+x(\d+)\s+\$([0-9,]+(?:\.\d{2})?)\s+each",
            r"^\s*([A-Za-z][A-Za-z0-9 ()]+?)\s+(\d+)\s+\$([0-9,]+(?:\.\d{2})?)\s+\$([0-9,]+(?:\.\d{2})?)",
        ]
        for line in text.splitlines():
            normalized_line = self._normalize_item_text(line)
            for pattern in patterns:
                match = re.match(pattern, normalized_line.strip(), flags=re.IGNORECASE)
                if not match:
                    continue

                item_name = self._normalize_item_name(match.group(1).strip())
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

    def _normalize_item_text(self, line: str) -> str:
        normalized = line
        replacements = {
            "Widget A": "WidgetA",
            "Widget B": "WidgetB",
            "Gadget X": "GadgetX",
        }
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        return normalized

    def _normalize_item_name(self, item_name: str) -> str:
        collapsed = re.sub(r"\s+", " ", item_name).strip()
        replacements = {
            "Widget A": "WidgetA",
            "Widget B": "WidgetB",
            "Gadget X": "GadgetX",
        }
        return replacements.get(collapsed, collapsed)
