from __future__ import annotations

import json
from pathlib import Path

from app.models import Invoice, LineItem
from app.parsers.base import BaseParser


class JsonInvoiceParser(BaseParser):
    def parse(self, invoice_path: Path) -> Invoice:
        payload = json.loads(invoice_path.read_text())
        vendor = payload.get("vendor") or {}
        line_items = [
            LineItem(
                item_name=item.get("item", ""),
                quantity=item.get("quantity"),
                unit_price=item.get("unit_price"),
                line_total=item.get("amount"),
                notes=item.get("note"),
            )
            for item in payload.get("line_items", [])
        ]
        return Invoice(
            invoice_number=payload.get("invoice_number"),
            vendor_name=vendor.get("name") if isinstance(vendor, dict) else str(vendor),
            invoice_date=payload.get("date"),
            due_date=payload.get("due_date"),
            currency=payload.get("currency") or "USD",
            line_items=line_items,
            subtotal=payload.get("subtotal"),
            tax_amount=payload.get("tax_amount"),
            total_amount=payload.get("total"),
            payment_terms=payload.get("payment_terms"),
        )
