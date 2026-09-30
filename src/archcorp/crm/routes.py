from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.orm import Session

from archcorp.crm.models import Contact, Customer, Opportunity
from archcorp.crm.service import MAX_PAGE_SIZE, ContactService, CustomerService, OpportunityService
from archcorp.infrastructure.db import get_session
from archcorp.observability import correlation_id_var
from archcorp.schemas import EXAMPLE_CUSTOMER_ID, EXAMPLE_CUSTOMER_RESPONSE, CustomerCreate, CustomerResponse, CustomerUpdate, Name, PartialUpdate
from archcorp.security import require_roles


router = APIRouter(prefix="/api/v1/crm", tags=["CRM"])
customers = CustomerService()
contacts = ContactService()
opportunities = OpportunityService()

# Matriz de autorização do CRM (docs/TDD_LOCALIZA.md).
CUSTOMER_READERS = require_roles("commercial", "contracts", "support", "admin")
CRM_WRITERS = require_roles("commercial", "admin")

PHONE_PATTERN = r"^\+[1-9]\d{7,14}$"
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
CONTACT_NOT_FOUND = {404: {"description": "Contato não encontrado."}}
OPPORTUNITY_NOT_FOUND = {404: {"description": "Oportunidade não encontrada."}}


class ContactInput(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{k: v for k, v in EXAMPLE_CONTACT.items() if k != "contactId"}]})

    customerId: UUID
    name: Name
    email: EmailStr
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN, description="Telefone no formato E.164.")


class ContactUpdate(PartialUpdate):
    model_config = ConfigDict(json_schema_extra={"examples": [{"phone": "+5531988880000"}]})
    non_nullable = frozenset({"name", "email"})
    null_message = "Nome e e-mail do contato não aceitam null"

    name: Name | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN, description="Telefone E.164; null remove o telefone.")


class OpportunityInput(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"customerId": EXAMPLE_CUSTOMER_ID, "title": EXAMPLE_OPPORTUNITY["title"], "notes": EXAMPLE_OPPORTUNITY["notes"]}]})

    customerId: UUID
    title: Name
    notes: str | None = Field(default=None, max_length=2000)


class OpportunityUpdate(PartialUpdate):
    """Altera estado, título ou notas. OPEN pode ir para WON ou LOST; WON e LOST são finais."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "WON"}, {"title": "Renovação de frota 2027 - fase 2", "notes": "Revisar volume"}]})
    non_nullable = frozenset({"status", "title"})
    null_message = "Estado e título da oportunidade não aceitam null"

    status: Literal["OPEN", "WON", "LOST"] | None = None
    title: Name | None = None
    notes: str | None = Field(default=None, max_length=2000)


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


def customer_data(item: Customer, legacy_id: str | None) -> dict:
    """Serializa o cliente no formato da API."""
    return {"customerId": item.customer_id, "name": item.name, "email": item.email,
            "eligible": item.eligible, "consentService": item.consent_service, "active": item.active,
            "legacyId": legacy_id}


def customer_with_legacy_id(session: Session, item: Customer) -> dict:
    """Serializa o cliente consultando o identificador legado do CRM."""
    return customer_data(item, CustomerService.legacy_ids(session, [item.customer_id]).get(item.customer_id))


def contact_data(item: Contact) -> dict:
    """Serializa o contato no formato da API."""
    return {"contactId": item.contact_id, "customerId": item.customer_id,
            "name": item.name, "email": item.email, "phone": item.phone}


def opportunity_data(item: Opportunity) -> dict:
    """Serializa a oportunidade no formato da API."""
    return {"opportunityId": item.opportunity_id, "customerId": item.customer_id,
            "title": item.title, "status": item.status, "notes": item.notes}


@router.post(
    "/customers",
    status_code=201,
    response_model=CustomerResponse,
    responses={
        201: {"description": "Cliente criado no CRM com identificador global.",
              "content": {"application/json": {"example": EXAMPLE_CUSTOMER_RESPONSE}}},
        409: {"description": "E-mail ou identificador legado já cadastrado."},
    },
    dependencies=[Depends(CRM_WRITERS)],
)
def create_customer(body: CustomerCreate, session: Session = Depends(get_session)) -> dict:
    """Cadastra cliente com identificador global e, opcionalmente, o identificador legado do CRM."""
    customer = customers.create(session, body.model_dump(mode="json"), correlation_id_var.get())
    return customer_data(customer, body.legacyId)


@router.get("/customers", response_model=list[CustomerResponse], dependencies=[Depends(CUSTOMER_READERS)])
def list_customers(
    email: EmailStr | None = None,
    legacyId: str | None = Query(default=None, max_length=100),
    active: bool | None = None,
    limit: int = Query(default=MAX_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> list[dict]:
    """Lista clientes com filtros por e-mail, identificador legado e situação, com paginação."""
    items = customers.list(session, email=email, legacy_id=legacyId, active=active, limit=limit, offset=offset)
    legacy_ids = CustomerService.legacy_ids(session, [x.customer_id for x in items])
    return [customer_data(x, legacy_ids.get(x.customer_id)) for x in items]


@router.get("/customers/{customer_id}", response_model=CustomerResponse, responses=CUSTOMER_NOT_FOUND, dependencies=[Depends(CUSTOMER_READERS)])
def get_customer(customer_id: UUID, session: Session = Depends(get_session)) -> dict:
    """Consulta um cliente pelo identificador global."""
    return customer_with_legacy_id(session, CustomerService.require(session, str(customer_id)))


@router.patch(
    "/customers/{customer_id}",
    response_model=CustomerResponse,
    responses={**CUSTOMER_NOT_FOUND, 409: {"description": "E-mail já cadastrado para outro cliente."}},
    dependencies=[Depends(CRM_WRITERS)],
)
def update_customer(customer_id: UUID, body: CustomerUpdate, session: Session = Depends(get_session)) -> dict:
    """Altera nome, e-mail, elegibilidade ou consentimento; nome ou e-mail alterados publicam CustomerUpdated.v1."""
    customer = customers.update(session, str(customer_id), body.model_dump(exclude_unset=True, mode="json"), correlation_id_var.get())
    return customer_with_legacy_id(session, customer)


@router.post("/customers/{customer_id}/deactivate", response_model=CustomerResponse, responses=CUSTOMER_NOT_FOUND, dependencies=[Depends(CRM_WRITERS)])
def deactivate_customer(customer_id: UUID, session: Session = Depends(get_session)) -> dict:
    """Inativa o cliente sem apagar o histórico; cliente inativo não origina reserva nem contrato."""
    return customer_with_legacy_id(session, customers.deactivate(session, str(customer_id), correlation_id_var.get()))


@router.post("/contacts", status_code=201, response_model=ContactResponse,
             responses={**CUSTOMER_NOT_FOUND, 409: {"description": "Contato com este e-mail já cadastrado para o cliente."}},
             dependencies=[Depends(CRM_WRITERS)])
def create_contact(body: ContactInput, session: Session = Depends(get_session)) -> dict:
    """Cadastra contato de um cliente existente."""
    return contact_data(contacts.create(session, body.model_dump(mode="json"), correlation_id_var.get()))


@router.get("/contacts", response_model=list[ContactResponse], dependencies=[Depends(CRM_WRITERS)])
def list_contacts(customerId: UUID | None = None, session: Session = Depends(get_session)) -> list[dict]:
    """Lista contatos, com filtro opcional por cliente."""
    return [contact_data(x) for x in contacts.list(session, str(customerId) if customerId else None)]


@router.get("/contacts/{contact_id}", response_model=ContactResponse, responses=CONTACT_NOT_FOUND, dependencies=[Depends(CRM_WRITERS)])
def get_contact(contact_id: UUID, session: Session = Depends(get_session)) -> dict:
    """Consulta um contato."""
    return contact_data(contacts.get(session, str(contact_id)))


@router.patch("/contacts/{contact_id}", response_model=ContactResponse,
              responses={**CONTACT_NOT_FOUND, 409: {"description": "Contato com este e-mail já cadastrado para o cliente."}},
              dependencies=[Depends(CRM_WRITERS)])
def update_contact(contact_id: UUID, body: ContactUpdate, session: Session = Depends(get_session)) -> dict:
    """Altera nome, e-mail ou telefone do contato."""
    return contact_data(contacts.update(session, str(contact_id), body.model_dump(exclude_unset=True, mode="json"), correlation_id_var.get()))


@router.delete("/contacts/{contact_id}", status_code=204, response_class=Response, responses=CONTACT_NOT_FOUND, dependencies=[Depends(CRM_WRITERS)])
def delete_contact(contact_id: UUID, session: Session = Depends(get_session)) -> Response:
    """Remove o contato."""
    contacts.delete(session, str(contact_id), correlation_id_var.get())
    return Response(status_code=204)


@router.post("/opportunities", status_code=201, response_model=OpportunityResponse, responses=CUSTOMER_NOT_FOUND, dependencies=[Depends(CRM_WRITERS)])
def create_opportunity(body: OpportunityInput, session: Session = Depends(get_session)) -> dict:
    """Cria oportunidade em aberto para um cliente existente."""
    return opportunity_data(opportunities.create(session, body.model_dump(mode="json"), correlation_id_var.get()))


@router.get("/opportunities", response_model=list[OpportunityResponse], dependencies=[Depends(CRM_WRITERS)])
def list_opportunities(customerId: UUID | None = None, status: Literal["OPEN", "WON", "LOST"] | None = None,
                       session: Session = Depends(get_session)) -> list[dict]:
    """Lista oportunidades, com filtros por cliente e estado."""
    return [opportunity_data(x) for x in opportunities.list(session, str(customerId) if customerId else None, status)]


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityResponse, responses=OPPORTUNITY_NOT_FOUND, dependencies=[Depends(CRM_WRITERS)])
def get_opportunity(opportunity_id: UUID, session: Session = Depends(get_session)) -> dict:
    """Consulta uma oportunidade."""
    return opportunity_data(opportunities.get(session, str(opportunity_id)))


@router.patch("/opportunities/{opportunity_id}", response_model=OpportunityResponse,
              responses={**OPPORTUNITY_NOT_FOUND, 409: {"description": "Oportunidade ganha ou perdida não muda de estado nem é editada."}},
              dependencies=[Depends(CRM_WRITERS)])
def update_opportunity(opportunity_id: UUID, body: OpportunityUpdate, session: Session = Depends(get_session)) -> dict:
    """Altera estado, título ou notas; OPEN pode ir para WON ou LOST, que são finais."""
    return opportunity_data(opportunities.update(session, str(opportunity_id), body.model_dump(exclude_unset=True), correlation_id_var.get()))
