from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Date, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from archcorp.infrastructure.db import Base


class Contract(Base):
    __tablename__ = "contracts_contracts"
    contract_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id: Mapped[str] = mapped_column(String(36), index=True)
    customer_name: Mapped[str] = mapped_column(String(150))
    customer_email: Mapped[str] = mapped_column(String(254))
    service_code: Mapped[str] = mapped_column(String(80))
    starts_on: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3))
    billing_cycle: Mapped[str] = mapped_column(String(20))
    sla_hours: Mapped[int] = mapped_column(default=8)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    __table_args__ = (UniqueConstraint("customer_id", "service_code", "starts_on", name="uq_contract_business_key"),)
