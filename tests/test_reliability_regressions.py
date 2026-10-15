"""Regressões da estabilização v1, sempre com dados sintéticos."""
import logging

from sqlalchemy import event, select

from archcorp.config import settings
from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import AuditLog, InboxEvent, OutboxEvent
from archcorp.integration.service import EventDispatcher, audit


def test_savepoint_apos_somente_leitura_nao_confirma_transacao_externa():
    # pysqlite adia o BEGIN: sem o ajuste em infrastructure/db.py, o SAVEPOINT
    # vira a transação externa e o RELEASE confirma o registro.
    with SessionLocal() as session:
        session.scalars(select(OutboxEvent)).all()
        with session.begin_nested():
            audit(session, "synthetic", "test", "savepoint", "success")
        session.rollback()
        assert session.scalars(select(AuditLog)).all() == []


def test_falha_de_consumidor_registra_tentativa_sem_liberar_bloqueio():
    """Entre a falha e o registro da tentativa não pode haver fim de transação.

    Um rollback completo nesse ponto libera o FOR UPDATE SKIP LOCKED e permite
    que outro despachante dispute o mesmo evento antes do novo bloqueio.
    """
    steps = []

    def broken(session, event_envelope):
        audit(session, event_envelope["correlationId"], "test", "broken", "success")
        session.flush()
        steps.append("failure")
        raise RuntimeError("falha sintética")

    def on_transaction_end(_session, transaction):
        if transaction.parent is None and steps:
            steps.append("end")

    def on_update(_mapper, _connection, target):
        steps.append(f"attempt:{target.attempts}")

    dispatcher = EventDispatcher({"Broken.v1": [("broken", broken)]})
    with SessionLocal() as session:
        session.add(OutboxEvent(event_type="Broken.v1", producer="test", payload={}, correlation_id="synthetic"))
        session.commit()
        event.listen(session, "after_transaction_end", on_transaction_end)
        event.listen(OutboxEvent, "before_update", on_update)
        try:
            assert dispatcher.dispatch_pending(session) == {"processed": 0, "failed": 1}
        finally:
            event.remove(OutboxEvent, "before_update", on_update)
            event.remove(session, "after_transaction_end", on_transaction_end)
        assert steps[:3] == ["failure", "attempt:1", "end"]
        assert session.scalars(select(AuditLog)).all() == []
        assert session.scalars(select(InboxEvent)).all() == []


def test_outbox_recupera_sessao_apos_erro_sql_e_continua(caplog):
    secret = "conteudo-sintetico-que-nao-pode-aparecer"

    def partial(session, event):
        audit(session, event["correlationId"], "test", "partial", "success")
        session.flush()

    def broken(session, _event):
        session.add(InboxEvent(event_id=None, consumer=secret))
        session.flush()

    dispatcher = EventDispatcher({"Broken.v1": [("partial", partial), ("broken", broken)]})
    with SessionLocal() as session:
        first = OutboxEvent(event_type="Broken.v1", producer="test", payload={}, correlation_id="synthetic")
        second = OutboxEvent(event_type="Healthy.v1", producer="test", payload={}, correlation_id="synthetic")
        session.add_all([first, second])
        session.commit()
        first_id, second_id = first.event_id, second.event_id
        with caplog.at_level(logging.WARNING):
            assert dispatcher.dispatch_pending(session) == {"processed": 1, "failed": 1}
        assert session.get(OutboxEvent, second_id).status == "PUBLISHED"
        for _ in range(settings.retry_limit - 1):
            assert dispatcher.dispatch_pending(session) == {"processed": 0, "failed": 1}
        failed = session.get(OutboxEvent, first_id)
        assert failed.status == "FAILED"
        assert failed.attempts == settings.retry_limit
        assert secret not in failed.last_error
        assert session.scalars(select(AuditLog)).all() == []
        assert session.scalars(select(InboxEvent)).all() == []
        failed.status, failed.attempts = "PENDING", 0
        session.commit()
        dispatcher.handlers["Broken.v1"] = [("partial", partial)]
        assert dispatcher.dispatch_pending(session) == {"processed": 1, "failed": 0}
        # Reentrega explícita mantém inbox e não repete efeitos.
        failed.status = "PENDING"
        session.commit()
        assert dispatcher.dispatch_pending(session) == {"processed": 1, "failed": 0}
        assert len(session.scalars(select(AuditLog)).all()) == 1
        assert len(session.scalars(select(InboxEvent)).all()) == 1
    assert secret not in caplog.text


def test_validacao_nao_ecoa_corpo_ou_contexto_sensivel(client, admin_headers):
    marker = "sintetico-segredo-privado"
    response = client.post("/api/v1/crm/customers", headers=admin_headers,
                           json={"email": marker, "token": marker})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["detail"] == body["errors"]
    assert marker not in response.text
    assert all(set(error) == {"type", "loc", "msg"} for error in body["errors"])


def test_resolve_repetido_sem_chave_preserva_conflito_v1(client, admin_headers, integrated_contract):
    customer, contract = integrated_contract
    client.post(f"/api/v1/contracts/{contract['contractId']}/activate",
                headers={**admin_headers, "Idempotency-Key": "activate-regression"})
    ticket = client.post("/api/v1/support/tickets", headers={**admin_headers, "Idempotency-Key": "ticket-regression"}, json={
        "customerId": customer["customerId"], "contractId": contract["contractId"],
        "serviceCode": "RENTAL-FLEX", "category": "QUESTION", "description": "Protocolo SEI 12345678901 em 2026-10-15T10:00:00Z",
    })
    assert ticket.status_code == 201
    path = f"/api/v1/support/tickets/{ticket.json()['ticketId']}/resolve"
    assert client.post(path, headers=admin_headers).status_code == 200
    repeated = client.post(path, headers=admin_headers)
    assert repeated.status_code == 409
    assert repeated.json()["code"] == "CONFLICT"


def test_reconcile_repetido_sem_chave_preserva_estado_invalido_v1(client, admin_headers, integrated_contract, monkeypatch):
    customer, contract = integrated_contract
    client.post(f"/api/v1/contracts/{contract['contractId']}/activate",
                headers={**admin_headers, "Idempotency-Key": "activate-pending"})
    monkeypatch.setattr(settings, "contract_adapter_available", False)
    ticket = client.post("/api/v1/support/tickets", headers={**admin_headers, "Idempotency-Key": "ticket-pending"}, json={
        "customerId": customer["customerId"], "contractId": contract["contractId"],
        "serviceCode": "RENTAL-FLEX", "category": "QUESTION", "description": "Consulta sintética durante indisponibilidade",
    }).json()
    monkeypatch.setattr(settings, "contract_adapter_available", True)
    path = f"/api/v1/support/tickets/{ticket['ticketId']}/reconcile"
    assert client.post(path, headers=admin_headers).status_code == 200
    repeated = client.post(path, headers=admin_headers)
    assert repeated.status_code == 409
    assert repeated.json()["code"] == "INVALID_STATE"
