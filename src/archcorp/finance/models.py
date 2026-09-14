from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Date, Numeric, String, UniqueConstraint
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
    __table_args__ = (UniqueConstraint("contract_id", name="uq_invoice_contract"),)
