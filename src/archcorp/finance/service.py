from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.finance.models import Invoice
from archcorp.integration.service import audit


def handle_contract_activated(session: Session, envelope: dict) -> None:
    payload = envelope["payload"]
    if session.scalar(select(Invoice).where(Invoice.contract_id == payload["contractId"])):
        return
    invoice = Invoice(
        contract_id=payload["contractId"], customer_id=payload["customerId"],
        amount=payload["billing"]["amount"], currency=payload["billing"]["currency"],
        due_date=date.today() + timedelta(days=10),
    )
    session.add(invoice)
    session.flush()
    audit(session, envelope["correlationId"], "finance", "create_first_invoice", "success", invoice.invoice_id, contractId=payload["contractId"])
