from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.infrastructure.db import get_session
from archcorp.integration.service import audit, enqueue
from archcorp.observability import correlation_id_var
from archcorp.schemas import EXAMPLE_TICKET_RESPONSE
from archcorp.security import require_roles
from archcorp.support.models import Ticket, TicketAssignment
from archcorp.support.service import TicketService


router = APIRouter(prefix="/api/v1/support", tags=["Atendimento e assistência 24h"])


EXAMPLE_TICKET_DETAIL = {**EXAMPLE_TICKET_RESPONSE, "description": "Serviço indisponível durante a demonstração", "owner": "Equipe de assistência"}
NOT_FOUND = {404: {"description": "Chamado não encontrado."}}


class AssignmentInput(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"owner": "Equipe de assistência"}]})

    owner: str = Field(min_length=2, max_length=80)


class TicketDetailResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_TICKET_DETAIL]})

    ticketId: UUID
    customerId: UUID
    contractId: UUID
    serviceCode: str
    category: str
    status: Literal["OPEN", "PENDING_ENTITLEMENT", "REJECTED_ENTITLEMENT", "RESOLVED"]
    priority: Literal["NORMAL", "HIGH"]
    slaHours: int | None
    dueAt: datetime | None
    description: str
    owner: str | None


def ticket_data(session: Session, item: Ticket) -> dict:
    assignment = session.get(TicketAssignment, item.ticket_id)
    return {**TicketService.as_dict(item), "description": item.description,
            "owner": assignment.owner if assignment else None}


@router.get("/tickets", response_model=list[TicketDetailResponse], dependencies=[Depends(require_roles("support", "operations", "admin"))])
def list_tickets(session: Session = Depends(get_session)) -> list[dict]:
    return [ticket_data(session, x) for x in session.scalars(select(Ticket).order_by(Ticket.ticket_id).limit(200))]


@router.get("/tickets/{ticket_id}", response_model=TicketDetailResponse, responses=NOT_FOUND, dependencies=[Depends(require_roles("support", "operations", "admin"))])
def get_ticket(ticket_id: UUID, session: Session = Depends(get_session)) -> dict:
    item = session.get(Ticket, str(ticket_id))
    if not item:
        raise HTTPException(404, "Chamado não encontrado")
    return ticket_data(session, item)


@router.post("/tickets/{ticket_id}/assign", response_model=TicketDetailResponse, responses={**NOT_FOUND, 409: {"description": "Chamado resolvido ou rejeitado não pode ser atribuído."}}, dependencies=[Depends(require_roles("support", "admin"))])
def assign_ticket(ticket_id: UUID, body: AssignmentInput, session: Session = Depends(get_session)) -> dict:
    item = session.get(Ticket, str(ticket_id))
    if not item:
        raise HTTPException(404, "Chamado não encontrado")
    if item.status not in {"OPEN", "PENDING_ENTITLEMENT"}:
        raise HTTPException(409, "Chamado não pode ser atribuído neste estado")
    assignment = session.get(TicketAssignment, str(ticket_id))
    if not assignment:
        assignment = TicketAssignment(ticket_id=str(ticket_id), owner=body.owner)
        session.add(assignment)
    else:
        assignment.owner = body.owner
    audit(session, correlation_id_var.get(), "support", "assign_ticket", "success", item.ticket_id)
    session.commit()
    return ticket_data(session, item)


@router.post("/tickets/{ticket_id}/resolve", response_model=TicketDetailResponse, responses={**NOT_FOUND, 409: {"description": "Somente chamado aberto pode ser resolvido."}}, dependencies=[Depends(require_roles("support", "admin"))])
def resolve_ticket(ticket_id: UUID, session: Session = Depends(get_session)) -> dict:
    item = session.get(Ticket, str(ticket_id))
    if not item:
        raise HTTPException(404, "Chamado não encontrado")
    if item.status != "OPEN":
        raise HTTPException(409, "Somente chamado aberto pode ser resolvido")
    item.status = "RESOLVED"
    enqueue(session, "TicketResolved.v1", "support", TicketService.as_dict(item), correlation_id_var.get())
    audit(session, correlation_id_var.get(), "support", "resolve_ticket", "success", item.ticket_id)
    session.commit()
    return ticket_data(session, item)
