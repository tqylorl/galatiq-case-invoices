from __future__ import annotations

import csv
from pathlib import Path

from app.models import Invoice, LineItem
from app.parsers.base import BaseParser


class CsvInvoiceParser(BaseParser):
    def parse(self, invoice_path: Path) -> Invoice:
        with invoice_path.open(newline="") as handle:
            rows = list(csv.reader(handle))

        if rows and len(rows[0]) == 2 and rows[0][0].strip().lower() == "field":
            return self._parse_key_value(rows[1:])
        return self._parse_line_items(rows)

    def _parse_key_value(self, rows: list[list[str]]) -> Invoice:
        invoice = Invoice()
        current_item: dict[str, str] = {}
        for key, value, *rest in rows:
            normalized_key = key.strip().lower()
            value = value.strip()
            if normalized_key == "invoice_number":
                invoice.invoice_number = value
            elif normalized_key == "vendor":
                invoice.vendor_name = value
            elif normalized_key == "date":
                invoice.invoice_date = value
            elif normalized_key == "due_date":
                invoice.due_date = value
            elif normalized_key == "item":
                if current_item:
                    invoice.line_items.append(self._build_item(current_item))
                current_item = {"item_name": value}
            elif normalized_key == "quantity":
                current_item["quantity"] = value
            elif normalized_key == "unit_price":
                current_item["unit_price"] = value
            elif normalized_key == "subtotal":
                invoice.subtotal = float(value)
            elif normalized_key == "tax":
                invoice.tax_amount = float(value)
            elif normalized_key == "total":
                invoice.total_amount = float(value)
            elif normalized_key == "payment_terms":
                invoice.payment_terms = value

        if current_item:
            invoice.line_items.append(self._build_item(current_item))
        return invoice

    def _parse_line_items(self, rows: list[list[str]]) -> Invoice:
        header = [cell.strip().lower() for cell in rows[0]]
        invoice = Invoice()
        for row in rows[1:]:
            if not any(cell.strip() for cell in row):
                continue
            data = dict(zip(header, row))
            if data.get("invoice number"):
                invoice.invoice_number = data.get("invoice number") or invoice.invoice_number
                invoice.vendor_name = data.get("vendor") or invoice.vendor_name
                invoice.invoice_date = data.get("date") or invoice.invoice_date
                invoice.due_date = data.get("due date") or invoice.due_date
                item_name = (data.get("item") or "").strip()
                qty_value = (data.get("qty") or "").strip()
                if item_name and qty_value:
                    invoice.line_items.append(
                        LineItem(
                            item_name=item_name,
                            quantity=float(qty_value),
                            unit_price=self._maybe_float(data.get("unit price")),
                            line_total=self._maybe_float(data.get("line total")),
                        )
                    )
            else:
                label = (row[-2] or "").strip().lower().rstrip(":")
                value = self._maybe_float(row[-1])
                if label == "subtotal":
                    invoice.subtotal = value
                elif label.startswith("tax"):
                    invoice.tax_amount = value
                elif label == "total":
                    invoice.total_amount = value
        return invoice

    def _build_item(self, values: dict[str, str]) -> LineItem:
        quantity = self._maybe_float(values.get("quantity"))
        unit_price = self._maybe_float(values.get("unit_price"))
        line_total = quantity * unit_price if quantity is not None and unit_price is not None else None
        return LineItem(
            item_name=values.get("item_name", ""),
            quantity=quantity,
            unit_price=unit_price,
            line_total=line_total,
        )

    def _maybe_float(self, value: str | None) -> float | None:
        if value is None or value == "":
            return None
        return float(str(value).replace("$", "").replace(",", "").strip())
