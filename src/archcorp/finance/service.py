"""Casos de uso do Financeiro: faturas por evento, pagamento simulado e inadimplência por vencimento.

Finance só conhece o contrato pelo payload dos eventos públicos de Contracts; não lê dados de outro
contexto. O pagamento é simulado: não há PSP, conciliação bancária, nota fiscal nem cobrança real.
"""
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from archcorp.config import settings
from archcorp.exceptions import BusinessRuleError, ConflictError, InvalidStateError, NotFoundError
from archcorp.finance.domain import (
    ZERO,
    Clock,
    InvoiceKind,
    InvoiceStatus,
    as_utc,
    billed_cycles,
    due_date_from,
    effective_status,
    ensure_invoice_transition,
    final_amount,
    money,
    status_after_payment,
    utc_now,
    utc_today,
)
from archcorp.finance.models import Invoice, Payment
from archcorp.integration.service import IdempotencyStore, audit
from archcorp.observability import logger


def iso_utc(moment: datetime | None) -> str | None:
    if moment is None:
        return None
    if moment.tzinfo is None:  # SQLite devolve sem fuso o que foi gravado em UTC
        moment = moment.replace(tzinfo=timezone.utc)
    return as_utc(moment).isoformat().replace("+00:00", "Z")


FINAL_BILLING_MARKER = "finance_final_billing"


def occurred_at(envelope: dict) -> datetime:
    return datetime.fromisoformat(envelope["occurredAt"].replace("Z", "+00:00"))


class FinanceService:
    def __init__(self, clock: Clock = utc_now):
        self.clock = clock

    # ---------- Consumidores de eventos ----------

    def handle_contract_activated(self, session: Session, envelope: dict) -> None:
        """Primeira fatura (`INITIAL`), única por contrato e por `eventId`."""
        payload = envelope["payload"]
        if self._by_event(session, envelope["eventId"]) or self._invoice_of(session, payload["contractId"], InvoiceKind.INITIAL):
            return
        billing = payload["billing"]
        invoice = Invoice(
            contract_id=payload["contractId"], customer_id=payload["customerId"], amount=money(billing["amount"]),
            currency=billing["currency"], due_date=due_date_from(occurred_at(envelope)), status=InvoiceStatus.OPEN,
            kind=InvoiceKind.INITIAL, source_event_id=envelope["eventId"],
        )
        session.add(invoice)
        session.flush()
        audit(session, envelope["correlationId"], "finance", "create_first_invoice", "success", invoice.invoice_id,
              contractId=payload["contractId"], eventId=envelope["eventId"], dueDate=invoice.due_date.isoformat())

    def handle_contract_closed(self, session: Session, envelope: dict) -> None:
        """Faturamento final (`FINAL`) por ciclo iniciado, idempotente por `eventId` e único por contrato.

        Todo encerramento processado deixa um marcador por `eventId` (`IdempotencyStore`), inclusive quando
        não há valor a faturar; assim a reentrega fora da inbox não repete nem a auditoria.
        """
        payload = envelope["payload"]
        contract_id = payload["contractId"]
        event_id = envelope["eventId"]
        marker = {"contractId": contract_id}
        if IdempotencyStore.replay(session, event_id, FINAL_BILLING_MARKER, marker, "eventId de encerramento já usado por outro contrato"):
            return
        if self._by_event(session, event_id) or self._invoice_of(session, contract_id, InvoiceKind.FINAL):
            return
        initial = self._invoice_of(session, contract_id, InvoiceKind.INITIAL)
        if initial is None:
            # Falha observável antes de qualquer escrita: o despachante conta a tentativa e o evento
            # pode ir para falhas; reprocessar depois da primeira fatura não duplica cobrança.
            raise BusinessRuleError(f"Faturamento final do contrato {contract_id} aguarda a primeira fatura")
        billing = payload["billing"]
        if billing["currency"] != initial.currency:
            raise BusinessRuleError("Moeda do encerramento diferente da primeira fatura")
        starts_on, ends_on = date.fromisoformat(payload["startsOn"]), date.fromisoformat(payload["endsOn"])
        # Inclui faturas canceladas: o cancelamento é definitivo e o encerramento não recobra seus ciclos
        # (decisão da revisão da T12, premissa a validar com o negócio).
        already = sum((money(i.amount) for i in self._invoices_of(session, contract_id)), ZERO)
        cycles = billed_cycles(starts_on, ends_on, billing["cycle"])
        amount = final_amount(billing["amount"], starts_on, ends_on, billing["cycle"], already)
        details = {"contractId": contract_id, "eventId": envelope["eventId"], "billedCycles": cycles,
                   "alreadyInvoiced": str(already), "currency": billing["currency"]}
        if amount == ZERO:
            audit(session, envelope["correlationId"], "finance", "create_final_invoice", "not_required", None, **details)
            IdempotencyStore.save(session, event_id, FINAL_BILLING_MARKER, marker, {"result": "not_required"})
            return
        invoice = Invoice(
            contract_id=contract_id, customer_id=payload["customerId"], amount=amount, currency=billing["currency"],
            due_date=due_date_from(occurred_at(envelope)), status=InvoiceStatus.OPEN, kind=InvoiceKind.FINAL,
            source_event_id=envelope["eventId"],
        )
        session.add(invoice)
        session.flush()
        audit(session, envelope["correlationId"], "finance", "create_final_invoice", "success", invoice.invoice_id,
              amount=str(amount), dueDate=invoice.due_date.isoformat(), **details)
        IdempotencyStore.save(session, event_id, FINAL_BILLING_MARKER, marker, {"result": "invoiced", "invoiceId": invoice.invoice_id})
        logger.info("Fatura final registrada", extra={"operation": "create_final_invoice", "result": "success"})

    # ---------- Comandos ----------

    def record_payment(self, session: Session, invoice_id: str, data: dict, idempotency_key: str | None,
                       correlation_id: str) -> tuple[dict, bool]:
        amount = money(data["amount"])
        request = {"invoiceId": invoice_id, "amount": str(amount), "currency": data["currency"], "reference": data["reference"]}
        if idempotency_key:
            stored = IdempotencyStore.replay(session, idempotency_key, "record_payment", request,
                                             "Idempotency-Key já utilizada com outro pagamento")
            if stored:
                return stored, True
        invoice = self._require(session, invoice_id, lock=True)
        if data["currency"] != invoice.currency:
            # `VALIDATION_ERROR` com detalhe textual: código que a versão 1 já devolvia neste caso.
            raise BusinessRuleError("Moeda diferente da fatura", code="VALIDATION_ERROR")
        prior = session.scalar(select(Payment).where(Payment.reference == data["reference"]))
        if prior:
            if prior.invoice_id != invoice.invoice_id or money(prior.amount) != amount:
                raise ConflictError("Referência de pagamento já usada")
            response = {"paymentId": prior.payment_id, "invoice": self.to_dict(session, invoice)}
            if idempotency_key:
                IdempotencyStore.save(session, idempotency_key, "record_payment", request, response)
                session.commit()
            return response, True
        paid = self.paid_total(session, invoice.invoice_id)
        target = status_after_payment(invoice.status, invoice.amount, paid, amount)
        payment = Payment(invoice_id=invoice.invoice_id, amount=amount, currency=data["currency"], reference=data["reference"])
        session.add(payment)
        invoice.status = target
        session.flush()
        response = {"paymentId": payment.payment_id, "invoice": self.to_dict(session, invoice, paid + amount)}
        if idempotency_key:
            IdempotencyStore.save(session, idempotency_key, "record_payment", request, response)
        # A referência informada pelo usuário não vai para a auditoria: pode conter dado sensível.
        audit(session, correlation_id, "finance", "record_simulated_payment", "success", payment.payment_id,
              invoiceId=invoice.invoice_id, amount=str(amount), currency=invoice.currency, status=str(target))
        session.commit()
        logger.info("Pagamento simulado registrado", extra={"operation": "record_simulated_payment", "result": str(target)})
        return response, False

    def evaluate_overdue(self, session: Session, as_of: date | None, correlation_id: str) -> dict:
        """Registra a inadimplência das faturas com saldo vencidas até `as_of` (data UTC).

        Idempotente pelo estado: uma fatura já `OVERDUE` não é marcada de novo.
        """
        now = as_utc(self.clock())
        today = now.date()
        reference = as_of or today
        if reference > today and (not settings.finance_allow_future_as_of or settings.public_demo):
            raise BusinessRuleError("Data de referência futura exige FINANCE_ALLOW_FUTURE_AS_OF=true (simulação local)")
        candidates = session.scalars(select(Invoice).where(
            Invoice.status.in_([InvoiceStatus.OPEN, InvoiceStatus.PARTIALLY_PAID]), Invoice.due_date < reference,
        ).order_by(Invoice.due_date, Invoice.invoice_id).with_for_update()).all()
        marked = []
        for invoice in candidates:
            balance = money(invoice.amount) - self.paid_total(session, invoice.invoice_id)
            if balance <= ZERO:
                logger.warning("Fatura sem saldo em estado aberto", extra={"operation": "evaluate_overdue", "result": "skipped"})
                continue
            ensure_invoice_transition(invoice.status, InvoiceStatus.OVERDUE)
            invoice.status = InvoiceStatus.OVERDUE
            invoice.overdue_since = now
            audit(session, correlation_id, "finance", "mark_invoice_overdue", "success", invoice.invoice_id,
                  asOf=reference.isoformat(), dueDate=invoice.due_date.isoformat(), balance=str(balance), currency=invoice.currency)
            marked.append(invoice.invoice_id)
        session.flush()
        already = (session.scalar(select(func.count()).select_from(Invoice).where(Invoice.status == InvoiceStatus.OVERDUE)) or 0) - len(marked)
        audit(session, correlation_id, "finance", "evaluate_overdue", "success", None,
              asOf=reference.isoformat(), simulated=reference != today, marked=len(marked), alreadyOverdue=already)
        session.commit()
        logger.info("Avaliação de inadimplência concluída", extra={"operation": "evaluate_overdue", "result": f"marked={len(marked)}"})
        return {"asOf": reference.isoformat(), "evaluatedAt": iso_utc(now), "markedOverdue": marked, "alreadyOverdue": already}

    def cancel(self, session: Session, invoice_id: str, reason: str, correlation_id: str) -> dict:
        invoice = self._require(session, invoice_id, lock=True)
        if invoice.status == InvoiceStatus.CANCELLED:
            return self.to_dict(session, invoice)
        if self.paid_total(session, invoice.invoice_id) > ZERO:
            raise InvalidStateError("Fatura com pagamento registrado não pode ser cancelada")
        ensure_invoice_transition(invoice.status, InvoiceStatus.CANCELLED)
        invoice.status = InvoiceStatus.CANCELLED
        audit(session, correlation_id, "finance", "cancel_invoice", "success", invoice.invoice_id, reason=reason)
        session.commit()
        return self.to_dict(session, invoice)

    # ---------- Consultas ----------

    def get(self, session: Session, invoice_id: str) -> dict:
        return self.to_dict(session, self._require(session, invoice_id))

    def list_invoices(self, session: Session, contract_id: str | None = None) -> list[dict]:
        query = select(Invoice).order_by(Invoice.due_date.desc(), Invoice.invoice_id).limit(200)
        if contract_id:
            query = query.where(Invoice.contract_id == contract_id)
        return [self.to_dict(session, item) for item in session.scalars(query)]

    def to_dict(self, session: Session, invoice: Invoice, paid: Decimal | None = None) -> dict:
        paid = self.paid_total(session, invoice.invoice_id) if paid is None else money(paid)
        balance = money(invoice.amount) - paid
        status = effective_status(invoice.status, invoice.due_date, balance, utc_today(self.clock))
        return {
            "invoiceId": invoice.invoice_id, "contractId": invoice.contract_id, "customerId": invoice.customer_id,
            "kind": invoice.kind, "amount": float(invoice.amount), "currency": invoice.currency,
            "dueDate": invoice.due_date.isoformat(), "paidAmount": float(paid), "balance": float(balance),
            "status": str(status), "delinquent": invoice.status == InvoiceStatus.OVERDUE,
            "overdueSince": iso_utc(invoice.overdue_since), "sourceEventId": invoice.source_event_id,
        }

    @staticmethod
    def paid_total(session: Session, invoice_id: str) -> Decimal:
        return sum((money(p.amount) for p in session.scalars(select(Payment).where(Payment.invoice_id == invoice_id))), ZERO)

    @staticmethod
    def _require(session: Session, invoice_id: str, lock: bool = False) -> Invoice:
        invoice = session.get(Invoice, invoice_id, with_for_update=lock)
        if not invoice:
            raise NotFoundError("Fatura não encontrada")
        return invoice

    @staticmethod
    def _by_event(session: Session, event_id: str) -> Invoice | None:
        return session.scalar(select(Invoice).where(Invoice.source_event_id == event_id))

    @staticmethod
    def _invoice_of(session: Session, contract_id: str, kind: InvoiceKind) -> Invoice | None:
        return session.scalar(select(Invoice).where(Invoice.contract_id == contract_id, Invoice.kind == kind))

    @staticmethod
    def _invoices_of(session: Session, contract_id: str) -> list[Invoice]:
        return list(session.scalars(select(Invoice).where(Invoice.contract_id == contract_id)))


def count_invoices(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Invoice)) or 0
