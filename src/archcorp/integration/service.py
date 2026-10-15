import hashlib
import json
from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from archcorp.config import settings
from archcorp.exceptions import ConflictError, IdempotencyConflictError
from archcorp.integration.models import AuditLog, IdempotencyRecord, InboxEvent, LegacyIdMapping, OutboxEvent
from archcorp.observability import COUNTERS, logger


EventHandler = Callable[[Session, dict], None]
BROKER_EXCHANGE = "archcorp.events"
BROKER_QUEUE = "archcorp.events.all"


class EventDispatcher:
    def __init__(self, handlers: dict[str, list[tuple[str, EventHandler]]]):
        self.handlers = handlers

    def dispatch_pending(self, session: Session) -> dict:
        event_ids = list(session.scalars(select(OutboxEvent.event_id).where(OutboxEvent.status == "PENDING")
                                        .order_by(OutboxEvent.occurred_at, OutboxEvent.event_id)))
        processed = failed = 0
        for event_id in event_ids:
            event = session.scalar(select(OutboxEvent).where(OutboxEvent.event_id == event_id,
                                   OutboxEvent.status == "PENDING").with_for_update(skip_locked=True))
            if event is None:
                continue
            try:
                # O savepoint isola consumidores e broker: em falha, desfaz só os
                # efeitos deste evento e mantém o bloqueio da linha na transação
                # externa, sem janela para outro despachante disputar a tentativa.
                with session.begin_nested():
                    for consumer, handler in self.handlers.get(event.event_type, []):
                        exists = session.scalar(select(InboxEvent).where(InboxEvent.event_id == event.event_id, InboxEvent.consumer == consumer))
                        if exists:
                            continue
                        handler(session, event.envelope())
                        session.add(InboxEvent(event_id=event.event_id, consumer=consumer))
                    session.flush()
                    self._publish_broker(event.envelope())
            except Exception as exc:
                self._register_failure(event)
                self._commit_attempt(session, event_id, exc)
                self._report_failure(event, exc)
                failed += 1
                continue
            event.status = "PUBLISHED"
            event.last_error = None
            try:
                session.commit()
            except Exception as exc:
                # Falha no commit externo invalida a transação e libera o bloqueio;
                # a tentativa é registrada em transação nova, se o evento seguir pendente.
                session.rollback()
                event = session.scalar(select(OutboxEvent).where(OutboxEvent.event_id == event_id).with_for_update())
                if event is None or event.status != "PENDING":
                    session.rollback()
                    continue
                self._register_failure(event)
                self._commit_attempt(session, event_id, exc)
                self._report_failure(event, exc)
                failed += 1
                continue
            processed += 1
            COUNTERS["events_published_total"] += 1
        return {"processed": processed, "failed": failed}

    @staticmethod
    def _commit_attempt(session: Session, event_id: str, cause: Exception) -> None:
        """Confirma a tentativa; se nem isso for possível, interrompe o lote.

        Sem gravar a tentativa, o banco está indisponível ou inconsistente e os
        próximos eventos falhariam igual. A transação é desfeita (o evento segue
        PENDING com a contagem anterior) e a falha sobe ao chamador.
        """
        try:
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.error("Falha ao registrar tentativa de despacho; lote interrompido",
                         extra={"operation": "dispatch_event", "result": "attempt_not_recorded", "eventId": event_id,
                                "errorType": f"{type(cause).__name__}/{type(exc).__name__}"})
            raise

    @staticmethod
    def _register_failure(event: OutboxEvent) -> None:
        event.attempts += 1
        event.last_error = "Falha no despacho do evento; consulte a correlação e reprocesse após corrigir a causa"
        if event.attempts >= settings.retry_limit:
            event.status = "FAILED"

    @staticmethod
    def _report_failure(event: OutboxEvent, exc: Exception) -> None:
        """Métrica e log só depois do commit que registrou a tentativa."""
        if event.status == "FAILED":
            COUNTERS["events_failed_total"] += 1
        # Não registrar exceção/traceback: SQLAlchemy inclui parâmetros
        # e adaptadores podem incluir payloads ou credenciais na mensagem.
        logger.warning("Falha ao despachar evento", extra={"operation": "dispatch_event", "result": "failure",
                       "eventId": event.event_id, "correlationId": event.correlation_id, "errorType": type(exc).__name__})

    @staticmethod
    def _publish_broker(envelope: dict) -> None:
        if not settings.rabbitmq_url:
            return
        import pika
        parameters = pika.URLParameters(settings.rabbitmq_url)
        # Sem esses limites, um broker que bloqueia publicadores (memória/disco)
        # prende o despacho e o bloqueio da linha da outbox indefinidamente.
        parameters.blocked_connection_timeout = settings.rabbitmq_blocked_timeout_seconds
        parameters.socket_timeout = settings.rabbitmq_socket_timeout_seconds
        parameters.heartbeat = settings.rabbitmq_heartbeat_seconds
        parameters.connection_attempts = 1
        connection = pika.BlockingConnection(parameters)
        try:
            channel = connection.channel()
            channel.exchange_declare(exchange=BROKER_EXCHANGE, exchange_type="topic", durable=True)
            # Fila durável que recebe todos os eventos: sem ela, uma mensagem sem
            # rota seria descartada pelo broker e o evento marcado PUBLISHED.
            # Cheia, recusa novas publicações (nack) em vez de descartar as antigas.
            declared = channel.queue_declare(queue=BROKER_QUEUE, durable=True, arguments={
                "x-max-length": settings.rabbitmq_queue_max_length, "x-overflow": "reject-publish"})
            COUNTERS["broker_queue_messages"] = declared.method.message_count
            channel.queue_bind(queue=BROKER_QUEUE, exchange=BROKER_EXCHANGE, routing_key="#")
            # Confirmação do broker: UnroutableError (mandatory), NackError (fila
            # cheia ou recusa) e ConnectionBlockedTimeout sobem para o despachante
            # e contam como falha da tentativa.
            channel.confirm_delivery()
            channel.basic_publish(
                exchange=BROKER_EXCHANGE,
                routing_key=envelope["eventType"],
                body=json.dumps(envelope, ensure_ascii=False).encode("utf-8"),
                properties=pika.BasicProperties(content_type="application/json", delivery_mode=2),
                mandatory=True,
            )
        finally:
            if connection.is_open:
                connection.close()


def audit(session: Session, correlation_id: str, module: str, operation: str, result: str, entity_id: str | None = None, **details) -> None:
    session.add(AuditLog(correlation_id=correlation_id, module=module, operation=operation, result=result, entity_id=entity_id, details=details))


def enqueue(session: Session, event_type: str, producer: str, payload: dict, correlation_id: str, causation_id: str | None = None) -> OutboxEvent:
    event = OutboxEvent(event_type=event_type, producer=producer, payload=payload, correlation_id=correlation_id, causation_id=causation_id)
    session.add(event)
    return event


class LegacyIdService:
    """Mapeia identificadores legados ao UUID global, sem regra de negócio dos contextos."""

    @staticmethod
    def register(session: Session, entity_type: str, global_id: str, source_system: str, legacy_id: str) -> LegacyIdMapping:
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
        return session.scalar(select(LegacyIdMapping).where(
            LegacyIdMapping.source_system == source_system, LegacyIdMapping.legacy_id == legacy_id,
        ))

    @staticmethod
    def legacy_ids(session: Session, global_id: str) -> list[LegacyIdMapping]:
        return list(session.scalars(select(LegacyIdMapping).where(LegacyIdMapping.global_id == global_id).order_by(LegacyIdMapping.id)))

    @staticmethod
    def count(session: Session) -> int:
        return session.scalar(select(func.count()).select_from(LegacyIdMapping)) or 0

    @staticmethod
    def as_dict(mapping: LegacyIdMapping) -> dict:
        return {"entityType": mapping.entity_type, "globalId": mapping.global_id,
                "sourceSystem": mapping.source_system, "legacyId": mapping.legacy_id}


class IdempotencyStore:
    """Guarda a resposta de um comando e a impressão digital da requisição."""

    @staticmethod
    def fingerprint(request: dict) -> str:
        canonical = json.dumps(request, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def replay(cls, session: Session, key: str, operation: str, request: dict, conflict_message: str) -> dict | None:
        stored = session.get(IdempotencyRecord, {"key": key, "operation": operation})
        if not stored:
            return None
        if stored.request_hash and stored.request_hash != cls.fingerprint(request):
            raise IdempotencyConflictError(conflict_message)
        return stored.response

    @classmethod
    def save(cls, session: Session, key: str, operation: str, request: dict, response: dict) -> None:
        session.add(IdempotencyRecord(key=key, operation=operation, response=response, request_hash=cls.fingerprint(request)))
