from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from archcorp.infrastructure.db import Base


class ProcessInstance(Base):
    __tablename__ = "workflow_instances"
    process_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    process_type: Mapped[str] = mapped_column(String(40))
    reference_id: Mapped[str] = mapped_column(String(36))
    customer_id: Mapped[str] = mapped_column(String(36), index=True)
    state: Mapped[str] = mapped_column(String(30), default="STARTED")
    owner: Mapped[str] = mapped_column(String(80), default="operations")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("process_type", "reference_id", name="uq_process_reference"),)
