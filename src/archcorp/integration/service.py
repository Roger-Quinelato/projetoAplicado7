import json
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.config import settings
from archcorp.integration.models import AuditLog, InboxEvent, OutboxEvent
from archcorp.observability import COUNTERS, logger


EventHandler = Callable[[Session, dict], None]


class EventDispatcher:
    def __init__(self, handlers: dict[str, list[tuple[str, EventHandler]]]):
        self.handlers = handlers

    def dispatch_pending(self, session: Session) -> dict:
        events = session.scalars(select(OutboxEvent).where(OutboxEvent.status == "PENDING").order_by(OutboxEvent.occurred_at)).all()
        processed = failed = 0
        for event in events:
            try:
                for consumer, handler in self.handlers.get(event.event_type, []):
                    exists = session.scalar(select(InboxEvent).where(InboxEvent.event_id == event.event_id, InboxEvent.consumer == consumer))
                    if exists:
                        continue
                    handler(session, event.envelope())
                    session.add(InboxEvent(event_id=event.event_id, consumer=consumer))
                self._publish_broker(event.envelope())
                event.status = "PUBLISHED"
                event.last_error = None
                processed += 1
                COUNTERS["events_published_total"] += 1
            except Exception as exc:
                event.attempts += 1
                event.last_error = str(exc)[:500]
                if event.attempts >= settings.retry_limit:
                    event.status = "FAILED"
                    COUNTERS["events_failed_total"] += 1
                failed += 1
                logger.exception("Falha ao despachar evento", extra={"operation": "dispatch_event", "result": "failure"})
            session.commit()
        return {"processed": processed, "failed": failed}

    @staticmethod
    def _publish_broker(envelope: dict) -> None:
        if not settings.rabbitmq_url:
            return
        import pika
        connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
        try:
            channel = connection.channel()
            channel.exchange_declare(exchange="archcorp.events", exchange_type="topic", durable=True)
            channel.basic_publish(
                exchange="archcorp.events",
                routing_key=envelope["eventType"],
                body=json.dumps(envelope, ensure_ascii=False).encode("utf-8"),
                properties=pika.BasicProperties(content_type="application/json", delivery_mode=2),
            )
        finally:
            connection.close()


def audit(session: Session, correlation_id: str, module: str, operation: str, result: str, entity_id: str | None = None, **details) -> None:
    session.add(AuditLog(correlation_id=correlation_id, module=module, operation=operation, result=result, entity_id=entity_id, details=details))


def enqueue(session: Session, event_type: str, producer: str, payload: dict, correlation_id: str, causation_id: str | None = None) -> OutboxEvent:
    event = OutboxEvent(event_type=event_type, producer=producer, payload=payload, correlation_id=correlation_id, causation_id=causation_id)
    session.add(event)
    return event
