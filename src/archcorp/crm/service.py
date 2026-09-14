from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.crm.models import Customer
from archcorp.crm.public import CustomerData
from archcorp.integration.models import LegacyIdMapping
from archcorp.integration.service import audit, enqueue


class CustomerService:
    def create(self, session: Session, data: dict, correlation_id: str) -> Customer:
        customer = Customer(name=data["name"], email=data["email"], eligible=data.get("eligible", True), consent_service=data.get("consentService", True))
        session.add(customer)
        session.flush()
        if data.get("legacyId"):
            session.add(LegacyIdMapping(entity_type="customer", global_id=customer.customer_id, source_system="CRM", legacy_id=data["legacyId"]))
        audit(session, correlation_id, "crm", "create_customer", "success", customer.customer_id)
        session.commit()
        return customer

    def update(self, session: Session, customer_id: str, data: dict, correlation_id: str) -> Customer | None:
        customer = session.get(Customer, customer_id)
        if not customer:
            return None
        for source, target in (("name", "name"), ("email", "email"), ("eligible", "eligible"), ("consentService", "consent_service")):
            if source in data and data[source] is not None:
                setattr(customer, target, data[source])
        enqueue(session, "CustomerUpdated.v1", "crm", {"customerId": customer.customer_id, "name": customer.name, "email": customer.email}, correlation_id)
        audit(session, correlation_id, "crm", "update_customer", "success", customer.customer_id)
        session.commit()
        return customer

    def get(self, session: Session, customer_id: str) -> CustomerData | None:
        customer = session.scalar(select(Customer).where(Customer.customer_id == customer_id))
        if not customer:
            return None
        return CustomerData(customer.customer_id, customer.name, customer.email, customer.eligible, customer.consent_service)
