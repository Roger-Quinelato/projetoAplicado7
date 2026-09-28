from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.crm.models import Contact, Customer, Opportunity
from archcorp.infrastructure.db import get_session
from archcorp.security import require_roles


router = APIRouter(prefix="/api/v1/crm", tags=["CRM"])


class ContactInput(BaseModel):
    customerId: UUID
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)


class OpportunityInput(BaseModel):
    customerId: UUID
    title: str = Field(min_length=2, max_length=150)
    notes: str | None = None


class OpportunityStatus(BaseModel):
    status: Literal["OPEN", "WON", "LOST"]


def customer_data(item: Customer) -> dict:
    return {"customerId": item.customer_id, "name": item.name, "email": item.email,
            "eligible": item.eligible, "consentService": item.consent_service}


def contact_data(item: Contact) -> dict:
    return {"contactId": item.contact_id, "customerId": item.customer_id,
            "name": item.name, "email": item.email, "phone": item.phone}


def opportunity_data(item: Opportunity) -> dict:
    return {"opportunityId": item.opportunity_id, "customerId": item.customer_id,
            "title": item.title, "status": item.status, "notes": item.notes}


@router.get("/customers", dependencies=[Depends(require_roles("commercial", "contracts", "support", "admin"))])
def list_customers(session: Session = Depends(get_session)) -> list[dict]:
    return [customer_data(x) for x in session.scalars(select(Customer).order_by(Customer.name).limit(200))]


@router.get("/customers/{customer_id}", dependencies=[Depends(require_roles("commercial", "contracts", "support", "admin"))])
def get_customer(customer_id: UUID, session: Session = Depends(get_session)) -> dict:
    item = session.get(Customer, str(customer_id))
    if not item:
        raise HTTPException(404, "Cliente não encontrado")
    return customer_data(item)


@router.post("/contacts", status_code=201, dependencies=[Depends(require_roles("commercial", "admin"))])
def create_contact(body: ContactInput, session: Session = Depends(get_session)) -> dict:
    if not session.get(Customer, str(body.customerId)):
        raise HTTPException(404, "Cliente não encontrado")
    item = Contact(customer_id=str(body.customerId), name=body.name, email=str(body.email), phone=body.phone)
    session.add(item)
    session.commit()
    return contact_data(item)


@router.get("/contacts", dependencies=[Depends(require_roles("commercial", "admin"))])
def list_contacts(customerId: UUID | None = None, session: Session = Depends(get_session)) -> list[dict]:
    query = select(Contact).order_by(Contact.name).limit(200)
    if customerId:
        query = query.where(Contact.customer_id == str(customerId))
    return [contact_data(x) for x in session.scalars(query)]


@router.post("/opportunities", status_code=201, dependencies=[Depends(require_roles("commercial", "admin"))])
def create_opportunity(body: OpportunityInput, session: Session = Depends(get_session)) -> dict:
    if not session.get(Customer, str(body.customerId)):
        raise HTTPException(404, "Cliente não encontrado")
    item = Opportunity(customer_id=str(body.customerId), title=body.title, notes=body.notes)
    session.add(item)
    session.commit()
    return opportunity_data(item)


@router.get("/opportunities", dependencies=[Depends(require_roles("commercial", "admin"))])
def list_opportunities(customerId: UUID | None = None, session: Session = Depends(get_session)) -> list[dict]:
    query = select(Opportunity).order_by(Opportunity.title).limit(200)
    if customerId:
        query = query.where(Opportunity.customer_id == str(customerId))
    return [opportunity_data(x) for x in session.scalars(query)]


@router.patch("/opportunities/{opportunity_id}", dependencies=[Depends(require_roles("commercial", "admin"))])
def update_opportunity(opportunity_id: UUID, body: OpportunityStatus, session: Session = Depends(get_session)) -> dict:
    item = session.get(Opportunity, str(opportunity_id))
    if not item:
        raise HTTPException(404, "Oportunidade não encontrada")
    item.status = body.status
    session.commit()
    return opportunity_data(item)
