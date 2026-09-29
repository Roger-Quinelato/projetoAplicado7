from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.crm.models import Customer
from archcorp.crm.public import CustomerData
from archcorp.exceptions import ConflictError
from archcorp.integration.service import LegacyIdService, audit, enqueue


LEGACY_SOURCE = "CRM"


class CustomerService:
    def create(self, session: Session, data: dict, correlation_id: str) -> Customer:
        self._ensure_unique_email(session, data["email"])
        if data.get("legacyId") and LegacyIdService.resolve(session, LEGACY_SOURCE, data["legacyId"]):
            raise ConflictError(f"Identificador legado {LEGACY_SOURCE}/{data['legacyId']} já cadastrado")
        customer = Customer(name=data["name"], email=data["email"], eligible=data.get("eligible", True), consent_service=data.get("consentService", True))
        session.add(customer)
        session.flush()
        if data.get("legacyId"):
            LegacyIdService.register(session, "customer", customer.customer_id, LEGACY_SOURCE, data["legacyId"])
        audit(session, correlation_id, "crm", "create_customer", "success", customer.customer_id)
        session.commit()
        return customer

    def update(self, session: Session, customer_id: str, data: dict, correlation_id: str) -> Customer | None:
        customer = session.get(Customer, customer_id)
        if not customer:
            return None
        if data.get("email") and data["email"] != customer.email:
            self._ensure_unique_email(session, data["email"], customer.customer_id)
        for source, target in (("name", "name"), ("email", "email"), ("eligible", "eligible"), ("consentService", "consent_service")):
            if source in data and data[source] is not None:
                setattr(customer, target, data[source])
        enqueue(session, "CustomerUpdated.v1", "crm", {"customerId": customer.customer_id, "name": customer.name, "email": customer.email}, correlation_id)
        audit(session, correlation_id, "crm", "update_customer", "success", customer.customer_id)
        session.commit()
        return customer

    @staticmethod
    def legacy_id(session: Session, customer_id: str) -> str | None:
        mappings = [m for m in LegacyIdService.legacy_ids(session, customer_id) if m.source_system == LEGACY_SOURCE]
        return mappings[0].legacy_id if mappings else None

    @staticmethod
    def _ensure_unique_email(session: Session, email: str, current_id: str | None = None) -> None:
        existing = session.scalar(select(Customer).where(Customer.email == email))
        if existing and existing.customer_id != current_id:
            raise ConflictError("E-mail já cadastrado no CRM")

    def get(self, session: Session, customer_id: str) -> CustomerData | None:
        customer = session.scalar(select(Customer).where(Customer.customer_id == customer_id))
        if not customer:
            return None
        return CustomerData(customer.customer_id, customer.name, customer.email, customer.eligible, customer.consent_service)
