from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from archcorp.infrastructure.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OutboxEvent(Base):
    __tablename__ = "integration_outbox"
    event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    event_version: Mapped[int] = mapped_column(Integer, default=1)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    correlation_id: Mapped[str] = mapped_column(String(64), index=True)
    causation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    producer: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def envelope(self) -> dict:
        return {
            "eventId": self.event_id,
            "eventType": self.event_type,
            "eventVersion": self.event_version,
            "occurredAt": self.occurred_at.isoformat().replace("+00:00", "Z"),
            "correlationId": self.correlation_id,
            "causationId": self.causation_id,
            "producer": self.producer,
            "payload": self.payload,
        }


class InboxEvent(Base):
    __tablename__ = "integration_inbox"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36))
    consumer: Mapped[str] = mapped_column(String(50))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("event_id", "consumer", name="uq_inbox_event_consumer"),)


class AuditLog(Base):
    __tablename__ = "integration_audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    correlation_id: Mapped[str] = mapped_column(String(64), index=True)
    module: Mapped[str] = mapped_column(String(50))
    operation: Mapped[str] = mapped_column(String(100))
    result: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)


class LegacyIdMapping(Base):
    __tablename__ = "integration_legacy_ids"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    global_id: Mapped[str] = mapped_column(String(36), index=True)
    source_system: Mapped[str] = mapped_column(String(50))
    legacy_id: Mapped[str] = mapped_column(String(100))
    __table_args__ = (UniqueConstraint("source_system", "legacy_id", name="uq_legacy_source_id"),)


class IdempotencyRecord(Base):
    __tablename__ = "integration_idempotency"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    operation: Mapped[str] = mapped_column(String(100), primary_key=True)
    response: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
