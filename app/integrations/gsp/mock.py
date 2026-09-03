from uuid import uuid4

from app.integrations.protocols import EWayBillRequest, EWayBillResponse, GspProvider


class MockGspProvider(GspProvider):
    async def generate_eway_bill(self, request: EWayBillRequest) -> EWayBillResponse:
        return EWayBillResponse(
            external_id=f"EWB-{uuid4().hex[:12].upper()}",
            status="generated",
            raw={"sandbox": True, "invoice_id": str(request.invoice_id)},
        )
