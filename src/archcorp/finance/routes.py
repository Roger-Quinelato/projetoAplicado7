from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.finance.models import Invoice, Payment
from archcorp.infrastructure.db import get_session
from archcorp.security import require_roles


router = APIRouter(prefix="/api/v1/finance", tags=["Financeiro e faturamento"])


class PaymentInput(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    reference: str = Field(min_length=3, max_length=100)


def invoice_data(item: Invoice, paid: Decimal) -> dict:
    status = item.status
    if status != "PAID" and item.due_date < date.today():
        status = "OVERDUE"
    return {"invoiceId": item.invoice_id, "contractId": item.contract_id,
            "customerId": item.customer_id, "amount": float(item.amount),
            "currency": item.currency, "dueDate": item.due_date.isoformat(),
            "paidAmount": float(paid), "status": status}


def paid_total(session: Session, invoice_id: str) -> Decimal:
    return sum((payment.amount for payment in session.scalars(select(Payment).where(Payment.invoice_id == invoice_id))), Decimal("0"))


@router.get("/invoices", dependencies=[Depends(require_roles("finance", "operations", "admin"))])
def list_invoices(session: Session = Depends(get_session)) -> list[dict]:
    return [invoice_data(x, paid_total(session, x.invoice_id)) for x in session.scalars(select(Invoice).order_by(Invoice.due_date.desc()).limit(200))]


@router.get("/invoices/{invoice_id}", dependencies=[Depends(require_roles("finance", "operations", "admin"))])
def get_invoice(invoice_id: UUID, session: Session = Depends(get_session)) -> dict:
    item = session.get(Invoice, str(invoice_id))
    if not item:
        raise HTTPException(404, "Fatura não encontrada")
    return invoice_data(item, paid_total(session, item.invoice_id))


@router.post("/invoices/{invoice_id}/payments", status_code=201, dependencies=[Depends(require_roles("finance", "admin"))])
def record_payment(invoice_id: UUID, body: PaymentInput, session: Session = Depends(get_session)) -> dict:
    item = session.get(Invoice, str(invoice_id))
    if not item:
        raise HTTPException(404, "Fatura não encontrada")
    if body.currency != item.currency:
        raise HTTPException(422, "Moeda diferente da fatura")
    prior = session.scalar(select(Payment).where(Payment.reference == body.reference))
    if prior:
        if prior.invoice_id != item.invoice_id or prior.amount != body.amount:
            raise HTTPException(409, "Referência de pagamento já usada")
        return {"paymentId": prior.payment_id, "invoice": invoice_data(item, paid_total(session, item.invoice_id))}
    total = paid_total(session, item.invoice_id)
    if item.status == "PAID" or total + body.amount > item.amount:
        raise HTTPException(409, "Pagamento excede saldo da fatura")
    payment = Payment(invoice_id=item.invoice_id, amount=body.amount,
                      currency=body.currency, reference=body.reference)
    session.add(payment)
    session.flush()
    if total + body.amount == item.amount:
        item.status = "PAID"
    session.commit()
    return {"paymentId": payment.payment_id, "invoice": invoice_data(item, total + body.amount)}


@router.get("/payments", dependencies=[Depends(require_roles("finance", "admin"))])
def list_payments(invoiceId: UUID | None = None, session: Session = Depends(get_session)) -> list[dict]:
    query = select(Payment).order_by(Payment.payment_id).limit(200)
    if invoiceId:
        query = query.where(Payment.invoice_id == str(invoiceId))
    return [{"paymentId": x.payment_id, "invoiceId": x.invoice_id, "amount": float(x.amount),
             "currency": x.currency, "reference": x.reference} for x in session.scalars(query)]
