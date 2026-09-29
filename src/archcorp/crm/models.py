from uuid import uuid4

from sqlalchemy import Boolean, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from archcorp.infrastructure.db import Base


class Customer(Base):
    __tablename__ = "crm_customers"
    customer_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_service: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class Contact(Base):
    __tablename__ = "crm_contacts"
    contact_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(254))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)


class Opportunity(Base):
    __tablename__ = "crm_opportunities"
    opportunity_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_id: Mapped[str] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
