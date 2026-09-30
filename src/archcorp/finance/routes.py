from datetime import date
from typing import Literal
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.finance.models import Invoice, Payment
from archcorp.finance.service import invoice_data, paid_total, record_payment as save_payment
from archcorp.infrastructure.db import get_session
from archcorp.observability import correlation_id_var
from archcorp.security import require_roles


router = APIRouter(prefix="/api/v1/finance", tags=["Financeiro e faturamento"])


EXAMPLE_INVOICE = {
    "invoiceId": "ffffffff-ffff-4fff-8fff-ffffffffffff",
    "contractId": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    "customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "amount": 2500.0,
    "currency": "BRL",
    "dueDate": "2026-10-11",
    "paidAmount": 0.0,
    "status": "OPEN",
}
EXAMPLE_PAYMENT = {
    "paymentId": "12121212-1212-4121-8121-121212121212",
    "invoiceId": EXAMPLE_INVOICE["invoiceId"],
    "amount": 2500.0,
    "currency": "BRL",
    "reference": "SIMULATED-001",
}
NOT_FOUND = {404: {"description": "Fatura não encontrada."}}


class PaymentInput(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"amount": 2500.00, "currency": "BRL", "reference": "SIMULATED-001"}]})

    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    reference: str = Field(min_length=3, max_length=100)


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_INVOICE]})

    invoiceId: UUID
    contractId: UUID
    customerId: UUID
    amount: float
    currency: str
    dueDate: date
    paidAmount: float
    status: Literal["OPEN", "PAID", "OVERDUE"]


class PaymentResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_PAYMENT]})

    paymentId: UUID
    invoiceId: UUID
    amount: float
    currency: str
    reference: str


class PaymentResultResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{
        "paymentId": EXAMPLE_PAYMENT["paymentId"],
        "invoice": {**EXAMPLE_INVOICE, "paidAmount": 2500.0, "status": "PAID"},
    }]})

    paymentId: UUID
    invoice: InvoiceResponse


@router.get("/invoices", response_model=list[InvoiceResponse], dependencies=[Depends(require_roles("finance", "operations", "admin"))])
def list_invoices(session: Session = Depends(get_session)) -> list[dict]:
    return [invoice_data(x, paid_total(session, x.invoice_id)) for x in session.scalars(select(Invoice).order_by(Invoice.due_date.desc()).limit(200))]


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse, responses=NOT_FOUND, dependencies=[Depends(require_roles("finance", "operations", "admin"))])
def get_invoice(invoice_id: UUID, session: Session = Depends(get_session)) -> dict:
    item = session.get(Invoice, str(invoice_id))
    if not item:
        raise HTTPException(404, "Fatura não encontrada")
    return invoice_data(item, paid_total(session, item.invoice_id))


@router.post(
    "/invoices/{invoice_id}/payments",
    status_code=201,
    response_model=PaymentResultResponse,
    responses={
        **NOT_FOUND,
        409: {"description": "Referência já usada em outro pagamento ou valor acima do saldo."},
        422: {"description": "Entrada inválida ou moeda diferente da fatura."},
    },
    dependencies=[Depends(require_roles("finance", "admin"))])
def record_payment(invoice_id: UUID, body: PaymentInput, session: Session = Depends(get_session)) -> dict:
    return save_payment(session, str(invoice_id), body.amount, body.currency, body.reference, correlation_id_var.get())


@router.get("/payments", response_model=list[PaymentResponse], dependencies=[Depends(require_roles("finance", "admin"))])
def list_payments(invoiceId: UUID | None = None, session: Session = Depends(get_session)) -> list[dict]:
    query = select(Payment).order_by(Payment.payment_id).limit(200)
    if invoiceId:
        query = query.where(Payment.invoice_id == str(invoiceId))
    return [{"paymentId": x.payment_id, "invoiceId": x.invoice_id, "amount": float(x.amount),
             "currency": x.currency, "reference": x.reference} for x in session.scalars(query)]
