from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.crm.models import Contact, Customer, Opportunity
from archcorp.crm.service import CustomerService
from archcorp.infrastructure.db import get_session
from archcorp.schemas import EXAMPLE_CUSTOMER_ID, CustomerResponse
from archcorp.security import require_roles


router = APIRouter(prefix="/api/v1/crm", tags=["CRM"])


EXAMPLE_CONTACT = {
    "contactId": "16161616-1616-4161-8161-161616161616",
    "customerId": EXAMPLE_CUSTOMER_ID,
    "name": "Pessoa Gestora Sintética",
    "email": "gestora@cliente-sintetico.example.com",
    "phone": "+5531999990000",
}
EXAMPLE_OPPORTUNITY = {
    "opportunityId": "17171717-1717-4171-8171-171717171717",
    "customerId": EXAMPLE_CUSTOMER_ID,
    "title": "Renovação de frota 2027",
    "status": "OPEN",
    "notes": "Proposta de 20 veículos compactos",
}
CUSTOMER_NOT_FOUND = {404: {"description": "Cliente não encontrado."}}


class ContactInput(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{k: v for k, v in EXAMPLE_CONTACT.items() if k != "contactId"}]})

    customerId: UUID
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)


class OpportunityInput(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"customerId": EXAMPLE_CUSTOMER_ID, "title": EXAMPLE_OPPORTUNITY["title"], "notes": EXAMPLE_OPPORTUNITY["notes"]}]})

    customerId: UUID
    title: str = Field(min_length=2, max_length=150)
    notes: str | None = None


class OpportunityStatus(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "WON"}]})

    status: Literal["OPEN", "WON", "LOST"]


class ContactResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_CONTACT]})

    contactId: UUID
    customerId: UUID
    name: str
    email: EmailStr
    phone: str | None


class OpportunityResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_OPPORTUNITY]})

    opportunityId: UUID
    customerId: UUID
    title: str
    status: Literal["OPEN", "WON", "LOST"]
    notes: str | None


def customer_data(item: Customer) -> dict:
    return {"customerId": item.customer_id, "name": item.name, "email": item.email,
            "eligible": item.eligible, "consentService": item.consent_service}


def contact_data(item: Contact) -> dict:
    return {"contactId": item.contact_id, "customerId": item.customer_id,
            "name": item.name, "email": item.email, "phone": item.phone}


def opportunity_data(item: Opportunity) -> dict:
    return {"opportunityId": item.opportunity_id, "customerId": item.customer_id,
            "title": item.title, "status": item.status, "notes": item.notes}


@router.get("/customers", response_model=list[CustomerResponse], dependencies=[Depends(require_roles("commercial", "contracts", "support", "admin"))])
def list_customers(session: Session = Depends(get_session)) -> list[dict]:
    return [customer_data(x) for x in session.scalars(select(Customer).order_by(Customer.name).limit(200))]


@router.get("/customers/{customer_id}", response_model=CustomerResponse, responses=CUSTOMER_NOT_FOUND, dependencies=[Depends(require_roles("commercial", "contracts", "support", "admin"))])
def get_customer(customer_id: UUID, session: Session = Depends(get_session)) -> dict:
    item = session.get(Customer, str(customer_id))
    if not item:
        raise HTTPException(404, "Cliente não encontrado")
    return {**customer_data(item), "legacyId": CustomerService.legacy_id(session, item.customer_id)}


@router.post("/contacts", status_code=201, response_model=ContactResponse, responses=CUSTOMER_NOT_FOUND, dependencies=[Depends(require_roles("commercial", "admin"))])
def create_contact(body: ContactInput, session: Session = Depends(get_session)) -> dict:
    if not session.get(Customer, str(body.customerId)):
        raise HTTPException(404, "Cliente não encontrado")
    item = Contact(customer_id=str(body.customerId), name=body.name, email=str(body.email), phone=body.phone)
    session.add(item)
    session.commit()
    return contact_data(item)


@router.get("/contacts", response_model=list[ContactResponse], dependencies=[Depends(require_roles("commercial", "admin"))])
def list_contacts(customerId: UUID | None = None, session: Session = Depends(get_session)) -> list[dict]:
    query = select(Contact).order_by(Contact.name).limit(200)
    if customerId:
        query = query.where(Contact.customer_id == str(customerId))
    return [contact_data(x) for x in session.scalars(query)]


@router.post("/opportunities", status_code=201, response_model=OpportunityResponse, responses=CUSTOMER_NOT_FOUND, dependencies=[Depends(require_roles("commercial", "admin"))])
def create_opportunity(body: OpportunityInput, session: Session = Depends(get_session)) -> dict:
    if not session.get(Customer, str(body.customerId)):
        raise HTTPException(404, "Cliente não encontrado")
    item = Opportunity(customer_id=str(body.customerId), title=body.title, notes=body.notes)
    session.add(item)
    session.commit()
    return opportunity_data(item)


@router.get("/opportunities", response_model=list[OpportunityResponse], dependencies=[Depends(require_roles("commercial", "admin"))])
def list_opportunities(customerId: UUID | None = None, session: Session = Depends(get_session)) -> list[dict]:
    query = select(Opportunity).order_by(Opportunity.title).limit(200)
    if customerId:
        query = query.where(Opportunity.customer_id == str(customerId))
    return [opportunity_data(x) for x in session.scalars(query)]


@router.patch("/opportunities/{opportunity_id}", response_model=OpportunityResponse, responses={404: {"description": "Oportunidade não encontrada."}}, dependencies=[Depends(require_roles("commercial", "admin"))])
def update_opportunity(opportunity_id: UUID, body: OpportunityStatus, session: Session = Depends(get_session)) -> dict:
    item = session.get(Opportunity, str(opportunity_id))
    if not item:
        raise HTTPException(404, "Oportunidade não encontrada")
    item.status = body.status
    session.commit()
    return opportunity_data(item)
