"""Regressões das três lacunas reproduzidas na revisão de entrega."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select

from archcorp.config import settings
from archcorp.exceptions import BusinessRuleError, InvalidStateError
from archcorp.finance.models import Invoice
from archcorp.finance.service import FinanceService
from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import InboxEvent, OutboxEvent
from archcorp.integration.service import EventDispatcher
from archcorp.integration.routes import reprocess
from archcorp.workflow import service as workflow
from archcorp.workflow.models import ProcessInstance, ProcessTask


def event(kind, offset=0, **payload):
    return OutboxEvent(event_type=kind, producer="support", correlation_id="regression",
                       occurred_at=datetime(2026, 10, 28, 10, tzinfo=timezone.utc) + timedelta(seconds=offset),
                       payload={"ticketId": "ticket", "customerId": "customer",
                                "dueAt": "2026-10-28T18:00:00Z", **payload})


@pytest.mark.parametrize("exhausted", [False, True])
def test_f3_resolucao_aguarda_abertura_e_reprocessa_sem_perder_conclusao(exhausted):
    failing = True

    def opening(session, envelope):
        if failing:
            raise RuntimeError("Indisponibilidade sintética")
        workflow.handle_ticket_opened(session, envelope)

    dispatcher = EventDispatcher({
        "TicketOpened.v1": [("opening", opening)],
        "TicketResolved.v1": [("resolution", workflow.handle_ticket_resolved)],
    })
    with SessionLocal() as session:
        opened, resolved = event("TicketOpened.v1"), event("TicketResolved.v1", 1)
        session.add_all([opened, resolved])
        session.commit()
        for _ in range(settings.retry_limit if exhausted else 1):
            assert dispatcher.dispatch_pending(session) == {"processed": 0, "failed": 2}
        # Dependência ausente nunca confirma a resolução ou sua inbox.
        assert session.scalar(select(InboxEvent).where(InboxEvent.event_id == resolved.event_id)) is None
        if exhausted:
            assert opened.status == resolved.status == "FAILED"
            reprocess(UUID(opened.event_id), session)
            reprocess(UUID(resolved.event_id), session)
        failing = False
        assert dispatcher.dispatch_pending(session) == {"processed": 2, "failed": 0}
        [process] = list(session.scalars(select(ProcessInstance)))
        assert process.state == "COMPLETED"
        assert [t.state for t in session.scalars(select(ProcessTask))] == ["DONE"]
        assert opened.status == resolved.status == "PUBLISHED"
        assert dispatcher.dispatch_pending(session) == {"processed": 0, "failed": 0}


@pytest.mark.parametrize("states,expected", [
    (["OPEN"], "CANCELLED"),
    (["DONE", "OPEN"], "CANCELLED"),
    (["DONE", "DONE"], "COMPLETED"),
])
def test_encerramento_do_contrato_respeita_agregado_e_tarefas_finais(states, expected):
    with SessionLocal() as session:
        process = ProcessInstance(process_type="ONBOARDING", reference_id="contract", customer_id="customer")
        session.add(process)
        session.flush()
        session.add_all(ProcessTask(process_id=process.process_id, title="Preparar", state=state) for state in states)
        session.commit()
        envelope = {"payload": {"contractId": "contract"}, "correlationId": "closing"}
        workflow.handle_contract_closed(session, envelope)
        session.commit()
        assert process.state == expected
        assert [t.state for t in session.scalars(select(ProcessTask))] == [
            "DONE" if state == "DONE" else "CANCELLED" for state in states]
        workflow.handle_contract_closed(session, envelope)
        assert process.state == expected


@pytest.mark.parametrize("today,allowed", [
    (date(2026, 10, 27), True),
    (date(2026, 10, 28), True),
    (date(2026, 10, 29), False),
])
def test_cancelamento_usa_mesmo_vencimento_utc_da_consulta(today, allowed):
    service = FinanceService(clock=lambda: datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc))
    with SessionLocal() as session:
        invoice = Invoice(contract_id="contract", customer_id="customer", amount=Decimal("10.00"),
                          currency="BRL", due_date=date(2026, 10, 28), status="OPEN", kind="INITIAL")
        session.add(invoice)
        session.commit()
        if allowed:
            assert service.cancel(session, invoice.invoice_id, "Ajuste sintético", "cancel")["status"] == "CANCELLED"
            assert service.cancel(session, invoice.invoice_id, "Repetição", "cancel")["status"] == "CANCELLED"
        else:
            assert service.get(session, invoice.invoice_id)["status"] == "OVERDUE"
            with pytest.raises(InvalidStateError):
                service.cancel(session, invoice.invoice_id, "Ajuste sintético", "cancel")
            session.rollback()
            assert invoice.status == "OPEN"  # recusa não grava inadimplência implicitamente


@pytest.mark.parametrize("handler", [workflow.handle_ticket_entitlement_reconciled, workflow.handle_contract_closed])
def test_dependencia_ausente_nao_confirma_evento(handler):
    with SessionLocal() as session:
        with pytest.raises(BusinessRuleError, match="aguarda"):
            handler(session, {"payload": {"ticketId": "missing", "contractId": "missing"}})


@pytest.mark.parametrize("handler", [workflow.handle_ticket_resolved, workflow.handle_ticket_entitlement_reconciled])
def test_evento_tardio_preserva_processo_e_tarefas_cancelados(handler):
    with SessionLocal() as session:
        process = ProcessInstance(process_type="TICKET_RESOLUTION", reference_id="ticket",
                                  customer_id="customer", state="CANCELLED")
        session.add(process)
        session.flush()
        task = ProcessTask(process_id=process.process_id, title="Resolução", state="CANCELLED", owner="Raquel")
        session.add(task)
        session.commit()
        handler(session, {"payload": {"ticketId": "ticket", "status": "OPEN", "dueAt": "2026-10-29T10:00:00Z"}})
        session.commit()
        assert (process.state, task.state, task.owner) == ("CANCELLED", "CANCELLED", "Raquel")
