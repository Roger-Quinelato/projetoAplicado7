"""Contexto financeiro e faturamento."""
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Date, DateTime, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from archcorp.infrastructure.db import Base


class Invoice(Base):
    __tablename__ = "finance_invoices"
    invoice_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    contract_id: Mapped[str] = mapped_column(String(36))
    customer_id: Mapped[str] = mapped_column(String(36), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3))
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    # 0004_finance_lifecycle: tipo (primeira fatura ou final), evento de origem e registro da inadimplência.
    kind: Mapped[str] = mapped_column(String(20), default="INITIAL", server_default="INITIAL")
    source_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    overdue_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        UniqueConstraint("contract_id", "kind", name="uq_invoice_contract_kind"),
        UniqueConstraint("source_event_id", name="uq_invoice_source_event"),
    )


class Payment(Base):
    __tablename__ = "finance_payments"
    payment_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    invoice_id: Mapped[str] = mapped_column(String(36), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3))
    reference: Mapped[str] = mapped_column(String(100), unique=True)
