"""Regressões da estabilização v1, sempre com dados sintéticos."""
import logging
import sys
import types
from datetime import datetime, timezone

import pytest
from sqlalchemy import event, select

from archcorp.config import settings
from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import AuditLog, InboxEvent, OutboxEvent
from archcorp.integration.service import EventDispatcher, audit
from archcorp.security import Principal
from archcorp.support.routes import acting_role
from archcorp.observability import COUNTERS, JsonFormatter


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


class _PublishError(Exception):
    """Substitui UnroutableError, NackError e ConnectionBlockedTimeout do pika."""


@pytest.fixture
def fake_pika(monkeypatch):
    """Substitui o pika por um dublê que registra a ordem das chamadas."""
    calls = {"order": [], "published": [], "fail_at": None, "parameters": None}

    def step(name, **kwargs):
        calls["order"].append(name)
        calls[name] = kwargs
        if calls["fail_at"] == name:
            raise _PublishError(name)

    class Channel:
        def exchange_declare(self, **kwargs):
            step("exchange_declare", **kwargs)

        def queue_declare(self, **kwargs):
            step("queue_declare", **kwargs)
            return types.SimpleNamespace(method=types.SimpleNamespace(message_count=7))

        def queue_bind(self, **kwargs):
            step("queue_bind", **kwargs)

        def confirm_delivery(self):
            step("confirm_delivery")

        def basic_publish(self, **kwargs):
            step("basic_publish", **kwargs)
            calls["published"].append(kwargs)

    class Connection:
        is_open = True

        def __init__(self, parameters):
            calls["parameters"] = parameters
            step("connect")

        def channel(self):
            return Channel()

        def close(self):
            calls["order"].append("close")

    module = types.SimpleNamespace(BlockingConnection=Connection, URLParameters=lambda url: types.SimpleNamespace(url=url),
                                   BasicProperties=lambda **kwargs: kwargs)
    monkeypatch.setitem(sys.modules, "pika", module)
    monkeypatch.setattr(settings, "rabbitmq_url", "amqp://sintetico")
    return calls


def test_broker_confirma_antes_de_publicar_com_limites_e_fila_declarada(fake_pika):
    dispatcher = EventDispatcher({})
    with SessionLocal() as session:
        session.add(OutboxEvent(event_type="Healthy.v1", producer="test", payload={}, correlation_id="synthetic"))
        session.commit()
        assert dispatcher.dispatch_pending(session) == {"processed": 1, "failed": 0}
    assert fake_pika["order"] == ["connect", "exchange_declare", "queue_declare", "queue_bind",
                                  "confirm_delivery", "basic_publish", "close"]
    parameters = fake_pika["parameters"]
    assert parameters.blocked_connection_timeout == settings.rabbitmq_blocked_timeout_seconds
    assert parameters.socket_timeout == settings.rabbitmq_socket_timeout_seconds
    assert parameters.heartbeat == settings.rabbitmq_heartbeat_seconds
    assert parameters.connection_attempts == 1
    assert fake_pika["queue_declare"] == {"queue": "archcorp.events.all", "durable": True, "arguments": {
        "x-max-length": settings.rabbitmq_queue_max_length, "x-overflow": "reject-publish"}}
    assert fake_pika["queue_bind"] == {"queue": "archcorp.events.all", "exchange": "archcorp.events", "routing_key": "#"}
    assert fake_pika["published"][0]["mandatory"] is True
    assert fake_pika["published"][0]["routing_key"] == "Healthy.v1"
    assert COUNTERS["broker_queue_messages"] == 7


@pytest.mark.parametrize("fail_at", ["connect", "exchange_declare", "queue_declare", "queue_bind",
                                     "confirm_delivery", "basic_publish"])
def test_falha_no_broker_nao_marca_publicado_e_desfaz_efeitos(fake_pika, fail_at):
    # basic_publish cobre mensagem sem rota, nack (fila cheia) e conexão bloqueada.
    fake_pika["fail_at"] = fail_at

    def effect(session, envelope):
        audit(session, envelope["correlationId"], "test", "effect", "success")

    dispatcher = EventDispatcher({"Routed.v1": [("effect", effect)]})
    with SessionLocal() as session:
        outbox = OutboxEvent(event_type="Routed.v1", producer="test", payload={}, correlation_id="synthetic")
        session.add(outbox)
        session.commit()
        assert dispatcher.dispatch_pending(session) == {"processed": 0, "failed": 1}
        stored = session.get(OutboxEvent, outbox.event_id)
        assert (stored.status, stored.attempts) == ("PENDING", 1)
        assert session.scalars(select(AuditLog)).all() == []
        assert session.scalars(select(InboxEvent)).all() == []
    assert "basic_publish" not in fake_pika["order"] or fail_at == "basic_publish"
    assert fake_pika["order"][-1] == "close" or fail_at == "connect"


def test_falha_ao_gravar_tentativa_interrompe_lote_sem_efeitos(caplog, monkeypatch):
    secret = "conteudo-sintetico-do-erro"

    def broken(_session, _envelope):
        raise RuntimeError(secret)

    dispatcher = EventDispatcher({"Broken.v1": [("broken", broken)]})
    with SessionLocal() as session:
        first = OutboxEvent(event_type="Broken.v1", producer="test", payload={}, correlation_id="synthetic")
        second = OutboxEvent(event_type="Healthy.v1", producer="test", payload={}, correlation_id="synthetic")
        session.add_all([first, second])
        session.commit()
        first_id, second_id = first.event_id, second.event_id
        original_commit = session.commit

        def failing_commit():
            raise RuntimeError(f"banco indisponível {secret}")

        monkeypatch.setattr(session, "commit", failing_commit)
        with caplog.at_level(logging.WARNING), pytest.raises(RuntimeError):
            dispatcher.dispatch_pending(session)
        monkeypatch.setattr(session, "commit", original_commit)
        # A transação foi desfeita: a sessão continua utilizável e nada foi gravado.
        assert session.get(OutboxEvent, first_id).attempts == 0
        assert session.get(OutboxEvent, first_id).status == "PENDING"
        assert session.get(OutboxEvent, second_id).status == "PENDING"
    records = [record for record in caplog.records if getattr(record, "result", None) == "attempt_not_recorded"]
    assert len(records) == 1
    assert records[0].errorType == "RuntimeError/RuntimeError"
    formatted = "".join(JsonFormatter().format(record) for record in caplog.records)
    assert secret not in formatted


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


def test_outbox_preserva_evento_anterior_confirmado():
    def healthy(session, event):
        audit(session, event["correlationId"], "test", "confirmed", "success")

    def broken(_session, _event):
        raise RuntimeError("falha sintética")

    dispatcher = EventDispatcher({"Healthy.v1": [("healthy", healthy)], "Broken.v1": [("broken", broken)]})
    with SessionLocal() as session:
        first = OutboxEvent(event_type="Healthy.v1", producer="test", payload={}, correlation_id="synthetic",
                            occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
        second = OutboxEvent(event_type="Broken.v1", producer="test", payload={}, correlation_id="synthetic",
                             occurred_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
        session.add_all([first, second])
        session.commit()
        assert dispatcher.dispatch_pending(session) == {"processed": 1, "failed": 1}
        assert first.status == "PUBLISHED" and second.status == "PENDING"
        assert len(list(session.scalars(select(AuditLog)))) == 1
        assert len(list(session.scalars(select(InboxEvent)))) == 1


def test_outbox_nao_contabiliza_falha_antes_de_confirmar_tentativa(monkeypatch):
    def broken(_session, _event):
        raise RuntimeError("falha sintética")

    def cannot_commit():
        raise RuntimeError("commit sintético indisponível")

    with SessionLocal() as session:
        session.add(OutboxEvent(event_type="Broken.v1", producer="test", payload={}, correlation_id="synthetic",
                                attempts=settings.retry_limit - 1))
        session.commit()
        previous = COUNTERS["events_failed_total"]
        monkeypatch.setattr(session, "commit", cannot_commit)
        with pytest.raises(RuntimeError, match="commit sintético"):
            EventDispatcher({"Broken.v1": [("broken", broken)]}).dispatch_pending(session)
        assert COUNTERS["events_failed_total"] == previous


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


def test_papel_auditado_e_autorizado_e_nao_o_primeiro_alfabetico():
    assert acting_role(Principal("synthetic", {"commercial", "support"})) == "support"
    assert acting_role(Principal("synthetic", {"finance", "operations"})) == "operations"


def test_replay_persistido_do_suporte_nao_muda_com_relogio_ou_estado(client, admin_headers, integrated_contract, monkeypatch):
    customer, contract = integrated_contract
    client.post(f"/api/v1/contracts/{contract['contractId']}/activate",
                headers={**admin_headers, "Idempotency-Key": "activate-replay"})
    monkeypatch.setattr(settings, "contract_adapter_available", False)
    ticket = client.post("/api/v1/support/tickets", headers={**admin_headers, "Idempotency-Key": "ticket-replay"}, json={
        "customerId": customer["customerId"], "contractId": contract["contractId"], "serviceCode": "RENTAL-FLEX",
        "category": "QUESTION", "description": "Protocolo SEI 12345678901 em 2026-10-15T10:00:00Z",
    }).json()
    monkeypatch.setattr(settings, "contract_adapter_available", True)
    path = f"/api/v1/support/tickets/{ticket['ticketId']}"
    headers = {**admin_headers, "Idempotency-Key": "reconcile-replay"}
    first = client.post(path + "/reconcile", headers=headers)
    assert first.status_code == 200
    resolve_headers = {**admin_headers, "Idempotency-Key": "resolve-replay"}
    resolved = client.post(path + "/resolve", headers=resolve_headers)
    assert resolved.status_code == 200
    replay = client.post(path + "/reconcile", headers=headers)
    assert replay.json() == first.json()
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert client.post(path + "/resolve", headers=resolve_headers).json() == resolved.json()
    conflict = client.post(path + "/resolve", headers=headers)
    assert conflict.status_code == 409 and conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"
    other = client.post("/api/v1/support/tickets", headers={**admin_headers, "Idempotency-Key": "ticket-replay-other"}, json={
        "customerId": customer["customerId"], "contractId": contract["contractId"], "serviceCode": "RENTAL-FLEX",
        "category": "QUESTION", "description": "Outra ocorrência sintética",
    }).json()
    conflict = client.post(f"/api/v1/support/tickets/{other['ticketId']}/resolve", headers=resolve_headers)
    assert conflict.status_code == 409 and conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"
    with SessionLocal() as session:
        assert len(session.scalars(select(OutboxEvent).where(OutboxEvent.event_type == "TicketResolved.v1")).all()) == 1
