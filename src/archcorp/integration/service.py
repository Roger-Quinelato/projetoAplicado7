import hashlib
import json
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.config import settings
from archcorp.infrastructure.db import count_rows
from archcorp.exceptions import ConflictError, IdempotencyConflictError
from archcorp.integration.models import AuditLog, IdempotencyRecord, InboxEvent, LegacyIdMapping, OutboxEvent
from archcorp.observability import COUNTERS, logger


EventHandler = Callable[[Session, dict], None]


class EventDispatcher:
    def __init__(self, handlers: dict[str, list[tuple[str, EventHandler]]]):
        """Recebe, por tipo de evento, a lista de consumidores (nome, handler)."""
        self.handlers = handlers

    def dispatch_pending(self, session: Session) -> dict:
        """Entrega os eventos pendentes aos consumidores sem repetir os já registrados na inbox; falhas contam tentativas até FAILED."""
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
        """Publica uma cópia do envelope no RabbitMQ quando RABBITMQ_URL está configurado."""
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
    """Registra uma entrada de auditoria vinculada ao correlationId."""
    session.add(AuditLog(correlation_id=correlation_id, module=module, operation=operation, result=result, entity_id=entity_id, details=details))


def enqueue(session: Session, event_type: str, producer: str, payload: dict, correlation_id: str, causation_id: str | None = None) -> OutboxEvent:
    """Grava um evento na outbox na mesma transação da mudança de negócio."""
    event = OutboxEvent(event_type=event_type, producer=producer, payload=payload, correlation_id=correlation_id, causation_id=causation_id)
    session.add(event)
    return event


class LegacyIdService:
    """Mapeia identificadores legados ao UUID global, sem regra de negócio dos contextos."""

    @staticmethod
    def register(session: Session, entity_type: str, global_id: str, source_system: str, legacy_id: str) -> LegacyIdMapping:
        """Associa o identificador legado ao UUID global; repetir a mesma associação não duplica."""
        existing = LegacyIdService.resolve(session, source_system, legacy_id)
        if existing:
            if existing.global_id != global_id:
                raise ConflictError(f"Identificador legado {source_system}/{legacy_id} já associado a outro registro")
            return existing
        mapping = LegacyIdMapping(entity_type=entity_type, global_id=global_id, source_system=source_system, legacy_id=legacy_id)
        session.add(mapping)
        return mapping

    @staticmethod
    def resolve(session: Session, source_system: str, legacy_id: str) -> LegacyIdMapping | None:
        """Busca o mapeamento de um identificador legado."""
        return session.scalar(select(LegacyIdMapping).where(
            LegacyIdMapping.source_system == source_system, LegacyIdMapping.legacy_id == legacy_id,
        ))

    @staticmethod
    def legacy_ids_by_global_id(session: Session, global_ids: list[str], source_system: str) -> dict[str, str]:
        """Mapeia UUIDs globais aos identificadores legados de um sistema de origem."""
        rows = session.execute(select(LegacyIdMapping.global_id, LegacyIdMapping.legacy_id).where(
            LegacyIdMapping.global_id.in_(global_ids), LegacyIdMapping.source_system == source_system,
        ).order_by(LegacyIdMapping.id.desc()))
        return {global_id: legacy_id for global_id, legacy_id in rows}

    @staticmethod
    def count(session: Session) -> int:
        """Conta os mapeamentos gravados."""
        return count_rows(session, LegacyIdMapping)

    @staticmethod
    def as_dict(mapping: LegacyIdMapping) -> dict:
        """Serializa o mapeamento no formato da API."""
        return {"entityType": mapping.entity_type, "globalId": mapping.global_id,
                "sourceSystem": mapping.source_system, "legacyId": mapping.legacy_id}


class IdempotencyStore:
    """Guarda a resposta de um comando e a impressão digital da requisição."""

    @staticmethod
    def fingerprint(request: dict) -> str:
        """Calcula o SHA-256 da requisição em JSON canônico."""
        canonical = json.dumps(request, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def replay(cls, session: Session, key: str, operation: str, request: dict, conflict_message: str) -> dict | None:
        """Devolve a resposta guardada para a chave; levanta conflito se a requisição mudou."""
        stored = session.get(IdempotencyRecord, {"key": key, "operation": operation})
        if not stored:
            return None
        if stored.request_hash and stored.request_hash != cls.fingerprint(request):
            raise IdempotencyConflictError(conflict_message)
        return stored.response

    @staticmethod
    def previous(session: Session, operation: str) -> dict | None:
        """Devolve a resposta de qualquer execução anterior da operação, se houver."""
        stored = session.scalar(select(IdempotencyRecord).where(IdempotencyRecord.operation == operation))
        return stored.response if stored else None

    @classmethod
    def save(cls, session: Session, key: str, operation: str, request: dict, response: dict) -> None:
        """Guarda a resposta e a impressão digital da requisição."""
        session.add(IdempotencyRecord(key=key, operation=operation, response=response, request_hash=cls.fingerprint(request)))
