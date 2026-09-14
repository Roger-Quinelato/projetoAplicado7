from uuid import uuid4

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from archcorp.infrastructure.db import Base


class Customer(Base):
    __tablename__ = "crm_customers"
    customer_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_service: Mapped[bool] = mapped_column(Boolean, default=True)
