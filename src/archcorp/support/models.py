from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from archcorp.infrastructure.db import Base


class Ticket(Base):
    __tablename__ = "support_tickets"
    ticket_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id: Mapped[str] = mapped_column(String(36), index=True)
    contract_id: Mapped[str] = mapped_column(String(36), index=True)
    service_code: Mapped[str] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30))
    priority: Mapped[str] = mapped_column(String(20))
    sla_hours: Mapped[int | None] = mapped_column(nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # T15 (migração 0004): anuláveis porque chamados anteriores não registraram esses instantes.
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TicketAssignment(Base):
    """Responsável atual; o histórico de atribuições fica em `TicketHistory`."""
    __tablename__ = "support_assignments"
    ticket_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner: Mapped[str] = mapped_column(String(80))


class TicketHistory(Base):
    """Histórico do chamado, propriedade de Support: abertura, atribuições, reconciliação e resolução.

    Não guarda a descrição do chamado nem credenciais; o ator é o papel que autorizou a operação.
    """
    __tablename__ = "support_ticket_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(String(36), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    action: Mapped[str] = mapped_column(String(30))
    from_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30))
    owner: Mapped[str | None] = mapped_column(String(80), nullable=True)
    previous_owner: Mapped[str | None] = mapped_column(String(80), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(30), nullable=True)
    sla_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(64), index=True)
