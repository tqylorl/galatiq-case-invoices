from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from app.models import Invoice, LineItem
from app.parsers.base import BaseParser


class XmlInvoiceParser(BaseParser):
    def parse(self, invoice_path: Path) -> Invoice:
        root = ET.fromstring(invoice_path.read_text())
        header = root.find("header")
        totals = root.find("totals")
        line_items: list[LineItem] = []
        for item in root.findall("./line_items/item"):
            line_items.append(
                LineItem(
                    item_name=(item.findtext("name") or "").strip(),
                    quantity=float(item.findtext("quantity") or 0),
                    unit_price=float(item.findtext("unit_price") or 0),
                )
            )

        return Invoice(
            invoice_number=header.findtext("invoice_number") if header is not None else None,
            vendor_name=header.findtext("vendor") if header is not None else None,
            invoice_date=header.findtext("date") if header is not None else None,
            due_date=header.findtext("due_date") if header is not None else None,
            currency=header.findtext("currency") if header is not None else "USD",
            line_items=line_items,
            subtotal=float(totals.findtext("subtotal") or 0) if totals is not None else None,
            tax_amount=float(totals.findtext("tax_amount") or 0) if totals is not None else None,
            total_amount=float(totals.findtext("total") or 0) if totals is not None else None,
            payment_terms=root.findtext("payment_terms"),
        )
