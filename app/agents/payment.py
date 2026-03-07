from __future__ import annotations

from app.models import Invoice, PaymentResult


def mock_payment(vendor: str, amount: float | None) -> dict[str, str]:
    return {"status": "success", "vendor": vendor, "amount": f"{amount or 0:.2f}"}


class PaymentAgent:
    def run(self, invoice: Invoice) -> PaymentResult:
        response = mock_payment(invoice.vendor_name or "UNKNOWN", invoice.total_amount)
        return PaymentResult(
            status=response["status"],
            message=f"Paid {response['amount']} to {response['vendor']}.",
            provider_response=response,
        )
