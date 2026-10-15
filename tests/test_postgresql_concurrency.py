"""Bloqueios reais, executados somente no PostgreSQL dedicado da CI."""
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock

import pytest
from sqlalchemy import event, select

from archcorp.exceptions import ConflictError
from archcorp.infrastructure.db import SessionLocal, engine
from archcorp.config import settings
from archcorp.integration.models import AuditLog, InboxEvent, OutboxEvent
from archcorp.integration.service import EventDispatcher, audit
from archcorp.main import tickets
from archcorp.support.models import Ticket, TicketAssignment, TicketHistory

pytestmark = pytest.mark.skipif(engine.dialect.name != "postgresql", reason="Exige PostgreSQL real")


@pytest.fixture
def ticket_id(client, admin_headers, integrated_contract):
    customer, contract = integrated_contract
    activated = client.post(f"/api/v1/contracts/{contract['contractId']}/activate",
                            headers={**admin_headers, "Idempotency-Key": "pg-activation"})
    assert activated.status_code == 200
    opened = client.post("/api/v1/support/tickets", headers={**admin_headers, "Idempotency-Key": "pg-ticket"}, json={
        "customerId": customer["customerId"], "contractId": contract["contractId"], "serviceCode": "RENTAL-FLEX",
        "category": "QUESTION", "description": "Concorrência sintética",
    })
    assert opened.status_code == 201
    return opened.json()["ticketId"]


def test_atribuicoes_concorrentes_preservam_cadeia_de_historico(ticket_id):
    barrier = Barrier(2)

    def assign(owner):
        with SessionLocal() as session:
            barrier.wait(timeout=10)
            return tickets.assign(session, ticket_id, owner, "synthetic", "support")

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(assign, ["Equipe A", "Equipe B"]))
    assert {result["owner"] for result in results} == {"Equipe A", "Equipe B"}
    with SessionLocal() as session:
        entries = list(session.scalars(select(TicketHistory).where(TicketHistory.ticket_id == ticket_id,
                                      TicketHistory.action.in_(["ASSIGNED", "REASSIGNED"])).order_by(TicketHistory.id)))
        assert len(entries) == 2
        assert entries[0].previous_owner is None
        assert entries[1].previous_owner == entries[0].owner
        assert session.get(TicketAssignment, ticket_id).owner == entries[1].owner
        assert len(list(session.scalars(select(AuditLog).where(AuditLog.operation == "assign_ticket")))) == 2


def test_assign_aguarda_bloqueio_de_resolve_e_nao_altera_resolvido(ticket_id):
    attempting_lock = Event()

    def assign():
        with SessionLocal() as session:
            def observe(_connection, _cursor, statement, _parameters, _context, _many):
                if "FOR UPDATE" in statement:
                    attempting_lock.set()
            event.listen(session.connection(), "before_cursor_execute", observe)
            with pytest.raises(ConflictError):
                tickets.assign(session, ticket_id, "Equipe tardia", "synthetic", "support")

    with ThreadPoolExecutor(max_workers=1) as executor, SessionLocal() as session:
        session.scalar(select(Ticket).where(Ticket.ticket_id == ticket_id).with_for_update())
        future = executor.submit(assign)
        assert attempting_lock.wait(timeout=10)
        tickets.resolve(session, ticket_id, "synthetic", "support", "pg-resolve")
        future.result(timeout=10)
    with SessionLocal() as session:
        assert session.get(Ticket, ticket_id).status == "RESOLVED"
        assert session.get(TicketAssignment, ticket_id) is None
        assert list(session.scalars(select(AuditLog).where(AuditLog.operation == "assign_ticket"))) == []
        assert len(list(session.scalars(select(OutboxEvent).where(OutboxEvent.event_type == "TicketResolved.v1")))) == 1


def _pending_event(event_type: str) -> str:
    with SessionLocal() as session:
        outbox = OutboxEvent(event_type=event_type, producer="test", payload={}, correlation_id="synthetic")
        session.add(outbox)
        session.commit()
        return outbox.event_id


def _dispatch(dispatcher: EventDispatcher) -> dict:
    with SessionLocal() as session:
        return dispatcher.dispatch_pending(session)


def test_segundo_despachante_pula_evento_bloqueado_enquanto_consumidor_falha():
    in_handler, release = Event(), Event()
    calls = []

    def broken(session, envelope):
        calls.append(envelope["eventId"])
        audit(session, envelope["correlationId"], "test", "broken", "success")
        session.flush()
        in_handler.set()
        assert release.wait(timeout=10)
        raise RuntimeError("falha sintética")

    dispatcher = EventDispatcher({"Broken.v1": [("broken", broken)]})
    event_id = _pending_event("Broken.v1")
    with ThreadPoolExecutor(max_workers=1) as executor:
        first = executor.submit(_dispatch, dispatcher)
        assert in_handler.wait(timeout=10)
        # Despachante B em outra conexão enquanto A segura o FOR UPDATE.
        second = _dispatch(dispatcher)
        release.set()
        assert first.result(timeout=20) == {"processed": 0, "failed": 1}
    assert second == {"processed": 0, "failed": 0}
    assert calls == [event_id]
    with SessionLocal() as session:
        stored = session.get(OutboxEvent, event_id)
        assert (stored.status, stored.attempts) == ("PENDING", 1)
        assert list(session.scalars(select(AuditLog))) == []
        assert list(session.scalars(select(InboxEvent))) == []


def test_despachantes_concorrentes_contam_cada_falha_uma_vez_ate_failed():
    guard = Lock()
    state = {"running": 0, "max_running": 0, "calls": 0}

    def broken(_session, _envelope):
        with guard:
            state["running"] += 1
            state["calls"] += 1
            state["max_running"] = max(state["max_running"], state["running"])
        try:
            time.sleep(0.05)
            raise RuntimeError("falha sintética")
        finally:
            with guard:
                state["running"] -= 1

    dispatcher = EventDispatcher({"Broken.v1": [("broken", broken)]})
    event_id = _pending_event("Broken.v1")
    barrier = Barrier(2)

    def worker():
        barrier.wait(timeout=10)
        for _ in range(settings.retry_limit * 10):
            _dispatch(dispatcher)
            with SessionLocal() as session:
                if session.get(OutboxEvent, event_id).status == "FAILED":
                    return

    with ThreadPoolExecutor(max_workers=2) as executor:
        for future in [executor.submit(worker) for _ in range(2)]:
            future.result(timeout=60)
    with SessionLocal() as session:
        stored = session.get(OutboxEvent, event_id)
        assert (stored.status, stored.attempts) == ("FAILED", settings.retry_limit)
    assert state["calls"] == settings.retry_limit
    assert state["max_running"] == 1
