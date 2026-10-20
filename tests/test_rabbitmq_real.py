"""Cópia no broker contra RabbitMQ real; executado só no job `rabbitmq` da CI."""
import json
import os

import pytest
from sqlalchemy import select

from archcorp.config import settings
from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import AuditLog, OutboxEvent
from archcorp.integration.service import BROKER_QUEUE, EventDispatcher, audit

RABBITMQ_URL = os.environ.get("TEST_RABBITMQ_URL")
pytestmark = pytest.mark.skipif(not RABBITMQ_URL, reason="Exige RabbitMQ real (TEST_RABBITMQ_URL)")


@pytest.fixture
def broker(monkeypatch):
    import pika
    monkeypatch.setattr(settings, "rabbitmq_url", RABBITMQ_URL)
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_delete(queue=BROKER_QUEUE)
    yield channel
    channel.queue_delete(queue=BROKER_QUEUE)
    connection.close()


def _event(session, event_type="Real.v1") -> str:
    outbox = OutboxEvent(event_type=event_type, producer="test", payload={"synthetic": True}, correlation_id="synthetic")
    session.add(outbox)
    session.commit()
    return outbox.event_id


def test_publicacao_confirmada_chega_a_fila_duravel(broker):
    with SessionLocal() as session:
        event_id = _event(session)
        assert EventDispatcher({}).dispatch_pending(session) == {"processed": 1, "failed": 0}
        assert session.get(OutboxEvent, event_id).status == "PUBLISHED"
    method, properties, body = broker.basic_get(queue=BROKER_QUEUE, auto_ack=True)
    assert method.routing_key == "Real.v1"
    assert properties.delivery_mode == 2
    assert json.loads(body)["eventId"] == event_id


def test_fila_cheia_recusa_publicacao_e_evento_fica_pendente(broker, monkeypatch):
    monkeypatch.setattr(settings, "rabbitmq_queue_max_length", 1)

    def effect(session, envelope):
        audit(session, envelope["correlationId"], "test", "effect", "success")

    dispatcher = EventDispatcher({"Real.v1": [("effect", effect)]})
    with SessionLocal() as session:
        first = _event(session)
        assert dispatcher.dispatch_pending(session) == {"processed": 1, "failed": 0}
        second = _event(session)
        # reject-publish: o broker devolve nack; o pika levanta NackError.
        assert dispatcher.dispatch_pending(session) == {"processed": 0, "failed": 1}
        stored = session.get(OutboxEvent, second)
        assert (stored.status, stored.attempts) == ("PENDING", 1)
        assert session.get(OutboxEvent, first).status == "PUBLISHED"
        assert len(session.scalars(select(AuditLog)).all()) == 1
    assert broker.queue_declare(queue=BROKER_QUEUE, passive=True).method.message_count == 1


def test_prontidao_informa_listener_amqp_ativo(broker, client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["broker"] == "UP"


def test_broker_indisponivel_nao_deixa_efeito_e_reprocessamento_recupera(broker, client, admin_headers, integrated_contract, monkeypatch):
    """Roteiro de falha e reprocessamento (plano, seção 6) com o RabbitMQ real na recuperação."""
    _, contract = integrated_contract
    contract_id = contract["contractId"]
    assert client.post(f"/api/v1/contracts/{contract_id}/activate", headers={**admin_headers, "Idempotency-Key": "real-act"}).status_code == 200
    monkeypatch.setattr(settings, "rabbitmq_url", "amqp://guest:guest@127.0.0.1:1/%2F")  # listener AMQP inalcançável
    assert client.get("/health/ready").json()["broker"] == "DOWN"

    for _ in range(settings.retry_limit):
        assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json() == {"processed": 0, "failed": 1}
    [failure] = client.get("/api/v1/integration/failures", headers=admin_headers).json()
    assert (failure["eventType"], failure["attempts"]) == ("ContractActivated.v1", settings.retry_limit)
    # Sem efeitos parciais: os consumidores foram desfeitos junto com a publicação recusada.
    assert client.get("/api/v1/finance/invoices", headers=admin_headers, params={"contractId": contract_id}).json() == []
    assert [p for p in client.get("/api/v1/workflow/processes", headers=admin_headers).json() if p["referenceId"] == contract_id] == []

    monkeypatch.setattr(settings, "rabbitmq_url", RABBITMQ_URL)
    assert client.get("/health/ready").json()["broker"] == "UP"
    assert client.post(f"/api/v1/integration/failures/{failure['eventId']}/reprocess", headers=admin_headers).status_code == 200
    assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json() == {"processed": 1, "failed": 0}
    assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json() == {"processed": 0, "failed": 0}

    assert len(client.get("/api/v1/finance/invoices", headers=admin_headers, params={"contractId": contract_id}).json()) == 1
    assert len([p for p in client.get("/api/v1/workflow/processes", headers=admin_headers).json() if p["referenceId"] == contract_id]) == 1
    assert broker.queue_declare(queue=BROKER_QUEUE, passive=True).method.message_count == 1
    method, _, body = broker.basic_get(queue=BROKER_QUEUE, auto_ack=True)
    assert method.routing_key == "ContractActivated.v1"
    assert json.loads(body)["eventId"] == failure["eventId"]
