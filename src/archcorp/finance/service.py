from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from archcorp.exceptions import BusinessRuleError, ConflictError, NotFoundError
from archcorp.finance.models import Invoice, Payment
from archcorp.integration.service import audit


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


def record_payment(session: Session, invoice_id: str, amount: Decimal, currency: str, reference: str, correlation_id: str) -> dict:
    item = session.scalar(select(Invoice).where(Invoice.invoice_id == invoice_id).with_for_update())
    if not item:
        raise NotFoundError("Fatura não encontrada")
    if amount <= 0 or amount != amount.quantize(Decimal("0.01")):
        raise BusinessRuleError("Pagamento deve ter valor positivo com até duas casas decimais")
    if currency != item.currency:
        raise BusinessRuleError("Moeda diferente da fatura")
    prior = session.scalar(select(Payment).where(Payment.reference == reference))
    if prior:
        if prior.invoice_id != item.invoice_id or prior.amount != amount:
            raise ConflictError("Referência de pagamento já usada")
        return {"paymentId": prior.payment_id, "invoice": invoice_data(item, paid_total(session, item.invoice_id))}
    total = paid_total(session, item.invoice_id)
    if item.status == "PAID" or total + amount > item.amount:
        raise ConflictError("Pagamento excede saldo da fatura")
    payment = Payment(invoice_id=item.invoice_id, amount=amount, currency=currency, reference=reference)
    session.add(payment)
    session.flush()
    if total + amount == item.amount:
        item.status = "PAID"
    audit(session, correlation_id, "finance", "record_payment", "success", payment.payment_id, invoiceId=item.invoice_id)
    session.commit()
    return {"paymentId": payment.payment_id, "invoice": invoice_data(item, total + amount)}


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


def count_invoices(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Invoice)) or 0
