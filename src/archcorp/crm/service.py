from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.crm.models import Contact, Customer, Opportunity
from archcorp.crm.public import CustomerData
from archcorp.exceptions import ConflictError, InvalidStateError
from archcorp.infrastructure.db import count_rows, get_or_raise
from archcorp.integration.service import LegacyIdService, audit, enqueue


LEGACY_SOURCE = "CRM"
MAX_PAGE_SIZE = 200
OPPORTUNITY_FINAL_STATES = {"WON", "LOST"}


def apply_changes(entity, data: dict, fields: dict[str, str]) -> list[str]:
    changed = [source for source, target in fields.items()
               if source in data and getattr(entity, target) != data[source]]
    for source in changed:
        setattr(entity, fields[source], data[source])
    return changed


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

    def update(self, session: Session, customer_id: str, data: dict, correlation_id: str) -> Customer:
        customer = self.require(session, customer_id)
        if data.get("email") and data["email"] != customer.email:
            self._ensure_unique_email(session, data["email"], customer.customer_id)
        values = {key: value for key, value in data.items() if value is not None}
        changed = apply_changes(customer, values, {"name": "name", "email": "email", "eligible": "eligible", "consentService": "consent_service"})
        if not changed:
            return customer
        if {"name", "email"}.intersection(changed):
            enqueue(session, "CustomerUpdated.v1", "crm", {"customerId": customer.customer_id, "name": customer.name, "email": customer.email}, correlation_id)
        audit(session, correlation_id, "crm", "update_customer", "success", customer.customer_id, fields=changed)
        session.commit()
        return customer

    def deactivate(self, session: Session, customer_id: str, correlation_id: str) -> Customer:
        customer = self.require(session, customer_id)
        if customer.active:
            customer.active = False
            audit(session, correlation_id, "crm", "deactivate_customer", "success", customer.customer_id)
            session.commit()
        return customer

    def list(self, session: Session, *, email: str | None = None, legacy_id: str | None = None, active: bool | None = None,
             limit: int = MAX_PAGE_SIZE, offset: int = 0) -> list[Customer]:
        query = select(Customer).order_by(Customer.name, Customer.customer_id)
        if email:
            query = query.where(Customer.email == email)
        if legacy_id:
            mapping = LegacyIdService.resolve(session, LEGACY_SOURCE, legacy_id)
            if not mapping:
                return []
            query = query.where(Customer.customer_id == mapping.global_id)
        if active is not None:
            query = query.where(Customer.active == active)
        return list(session.scalars(query.limit(min(limit, MAX_PAGE_SIZE)).offset(offset)))

    @staticmethod
    def count(session: Session) -> int:
        return count_rows(session, Customer)

    @staticmethod
    def legacy_ids(session: Session, customer_ids: Sequence[str]) -> dict[str, str]:
        return LegacyIdService.legacy_ids_by_global_id(session, customer_ids, LEGACY_SOURCE)

    @staticmethod
    def require(session: Session, customer_id: str) -> Customer:
        return get_or_raise(session, Customer, customer_id, "Cliente não encontrado")

    @staticmethod
    def _ensure_unique_email(session: Session, email: str, current_id: str | None = None) -> None:
        existing = session.scalar(select(Customer).where(Customer.email == email))
        if existing and existing.customer_id != current_id:
            raise ConflictError("E-mail já cadastrado no CRM")

    def get(self, session: Session, customer_id: str) -> CustomerData | None:
        customer = session.get(Customer, customer_id)
        if not customer:
            return None
        return CustomerData(customer.customer_id, customer.name, customer.email, customer.eligible, customer.consent_service, customer.active)


class ContactService:
    def create(self, session: Session, data: dict, correlation_id: str) -> Contact:
        CustomerService.require(session, data["customerId"])
        self._ensure_unique_email(session, data["customerId"], data["email"])
        contact = Contact(customer_id=data["customerId"], name=data["name"], email=data["email"], phone=data.get("phone"))
        session.add(contact)
        session.flush()
        audit(session, correlation_id, "crm", "create_contact", "success", contact.contact_id, customerId=contact.customer_id)
        session.commit()
        return contact

    def get(self, session: Session, contact_id: str) -> Contact:
        return get_or_raise(session, Contact, contact_id, "Contato não encontrado")

    def list(self, session: Session, customer_id: str | None = None) -> list[Contact]:
        query = select(Contact).order_by(Contact.name, Contact.contact_id).limit(MAX_PAGE_SIZE)
        if customer_id:
            query = query.where(Contact.customer_id == customer_id)
        return list(session.scalars(query))

    def update(self, session: Session, contact_id: str, data: dict, correlation_id: str) -> Contact:
        contact = self.get(session, contact_id)
        if data.get("email") and data["email"] != contact.email:
            self._ensure_unique_email(session, contact.customer_id, data["email"], contact.contact_id)
        changed = apply_changes(contact, data, {"name": "name", "email": "email", "phone": "phone"})
        if changed:
            audit(session, correlation_id, "crm", "update_contact", "success", contact.contact_id, fields=changed)
            session.commit()
        return contact

    def delete(self, session: Session, contact_id: str, correlation_id: str) -> None:
        contact = self.get(session, contact_id)
        session.delete(contact)
        audit(session, correlation_id, "crm", "delete_contact", "success", contact_id, customerId=contact.customer_id)
        session.commit()

    @staticmethod
    def _ensure_unique_email(session: Session, customer_id: str, email: str, current_id: str | None = None) -> None:
        existing = session.scalar(select(Contact).where(Contact.customer_id == customer_id, Contact.email == email))
        if existing and existing.contact_id != current_id:
            raise ConflictError("Contato com este e-mail já cadastrado para o cliente")


class OpportunityService:
    def create(self, session: Session, data: dict, correlation_id: str) -> Opportunity:
        CustomerService.require(session, data["customerId"])
        opportunity = Opportunity(customer_id=data["customerId"], title=data["title"], notes=data.get("notes"))
        session.add(opportunity)
        session.flush()
        audit(session, correlation_id, "crm", "create_opportunity", "success", opportunity.opportunity_id, customerId=opportunity.customer_id)
        session.commit()
        return opportunity

    def get(self, session: Session, opportunity_id: str) -> Opportunity:
        return get_or_raise(session, Opportunity, opportunity_id, "Oportunidade não encontrada")

    def list(self, session: Session, customer_id: str | None = None, status: str | None = None) -> list[Opportunity]:
        query = select(Opportunity).order_by(Opportunity.title, Opportunity.opportunity_id).limit(MAX_PAGE_SIZE)
        if customer_id:
            query = query.where(Opportunity.customer_id == customer_id)
        if status:
            query = query.where(Opportunity.status == status)
        return list(session.scalars(query))

    def update(self, session: Session, opportunity_id: str, data: dict, correlation_id: str) -> Opportunity:
        opportunity = self.get(session, opportunity_id)
        new_status = data.get("status")
        if new_status and new_status != opportunity.status:
            if opportunity.status in OPPORTUNITY_FINAL_STATES:
                raise InvalidStateError(f"Oportunidade {opportunity.status} não pode mudar para {new_status}")
        elif opportunity.status in OPPORTUNITY_FINAL_STATES and ({"title", "notes"} & data.keys()):
            raise InvalidStateError(f"Oportunidade {opportunity.status} não pode ser editada")
        changed = apply_changes(opportunity, data, {"status": "status", "title": "title", "notes": "notes"})
        if changed:
            audit(session, correlation_id, "crm", "update_opportunity", "success", opportunity.opportunity_id, fields=changed, status=opportunity.status)
            session.commit()
        return opportunity
