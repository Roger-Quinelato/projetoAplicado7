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
