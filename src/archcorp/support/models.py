from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
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
