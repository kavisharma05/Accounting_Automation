from uuid import uuid4

from app.integrations.protocols import EInvoiceProvider, EWayBillRequest, EWayBillResponse, GspProvider


class MockGspProvider(GspProvider):
    async def generate_eway_bill(self, request: EWayBillRequest) -> EWayBillResponse:
        return EWayBillResponse(
            external_id=f"EWB-{uuid4().hex[:12].upper()}",
            status="generated",
            raw={"sandbox": True, "invoice_id": str(request.invoice_id)},
        )


class MockEInvoiceProvider(EInvoiceProvider):
    async def generate_einvoice(self, invoice_id, payload: dict) -> dict:
        return {
            "irn": f"IRN-{uuid4().hex[:16].upper()}",
            "ack_no": f"ACK{uuid4().hex[:8].upper()}",
            "status": "generated",
            "sandbox": True,
            "invoice_id": str(invoice_id),
            "payload": payload,
        }
