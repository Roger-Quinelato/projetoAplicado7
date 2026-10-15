from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy.orm import Session

from archcorp.infrastructure.db import get_session
from archcorp.observability import correlation_id_var
from archcorp.schemas import EXAMPLE_CORRELATION_ID, EXAMPLE_PENDING_TICKET_RESPONSE, EXAMPLE_TICKET_RESPONSE
from archcorp.security import Principal, require_roles
from archcorp.support.service import PENDING_BATCH_MAX, TicketService


router = APIRouter(prefix="/api/v1/support", tags=["Atendimento e assistência 24h"])

# Matriz de autorização do atendimento (docs/TDD_LOCALIZA.md).
TICKET_READERS = require_roles("support", "operations", "admin")
TICKET_AGENTS = require_roles("support", "admin")
TICKET_RECONCILERS = require_roles("support", "operations", "admin")

SlaStatusValue = Literal["PENDING", "WITHIN", "BREACHED", "MET", "NOT_APPLICABLE"]
EXAMPLE_TICKET_DETAIL = {**EXAMPLE_TICKET_RESPONSE, "description": "Serviço indisponível durante a demonstração", "owner": "Equipe de assistência"}
EXAMPLE_RESOLVED_DETAIL = {**EXAMPLE_TICKET_DETAIL, "status": "RESOLVED", "resolvedAt": "2026-10-01T12:10:00Z", "slaStatus": "MET"}
EXAMPLE_HISTORY = [
    {"occurredAt": "2026-10-01T10:10:00Z", "action": "OPENED", "fromStatus": None, "toStatus": "OPEN", "owner": None,
     "previousOwner": None, "actorRole": "support", "slaStatus": "WITHIN", "correlationId": EXAMPLE_CORRELATION_ID},
    {"occurredAt": "2026-10-01T10:20:00Z", "action": "ASSIGNED", "fromStatus": "OPEN", "toStatus": "OPEN",
     "owner": "Equipe de assistência", "previousOwner": None, "actorRole": "support", "slaStatus": "WITHIN",
     "correlationId": EXAMPLE_CORRELATION_ID},
    {"occurredAt": "2026-10-01T11:00:00Z", "action": "REASSIGNED", "fromStatus": "OPEN", "toStatus": "OPEN",
     "owner": "Equipe de pátio", "previousOwner": "Equipe de assistência", "actorRole": "admin", "slaStatus": "WITHIN",
     "correlationId": EXAMPLE_CORRELATION_ID},
    {"occurredAt": "2026-10-01T12:10:00Z", "action": "RESOLVED", "fromStatus": "OPEN", "toStatus": "RESOLVED",
     "owner": "Equipe de pátio", "previousOwner": None, "actorRole": "support", "slaStatus": "MET",
     "correlationId": EXAMPLE_CORRELATION_ID},
]
EXAMPLE_PENDING_SUMMARY = {
    "confirmed": 1, "rejected": 0, "remaining": 0, "contractsAvailable": True,
    "tickets": [{**EXAMPLE_PENDING_TICKET_RESPONSE, "status": "OPEN", "slaHours": 8, "dueAt": "2026-10-01T18:10:00Z", "slaStatus": "WITHIN"}],
}
NOT_FOUND = {404: {"description": "Chamado não encontrado."}}
REPLAY_HEADER = {"Idempotency-Replayed": {
    "description": "true quando a mesma chave recupera a resposta persistida.",
    "schema": {"type": "string", "enum": ["true", "false"]}, "example": "false",
}}


class _Services:
    tickets: TicketService | None = None


def configure(tickets: TicketService) -> None:
    """Recebe o serviço montado pela composição da aplicação (porta de Contracts e relógio)."""
    _Services.tickets = tickets


def ticket_service() -> TicketService:
    return _Services.tickets


def acting_role(principal: Principal) -> str:
    """Papel registrado no histórico e na auditoria; nunca o token."""
    return next(role for role in ("admin", "support", "operations") if role in principal.roles)


Owner = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]


class AssignmentInput(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"owner": "Equipe de assistência"}]})

    owner: Owner = Field(description="Equipe ou função responsável; sem e-mail, telefone ou documento.")



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
    openedAt: datetime | None = Field(default=None, description="Abertura em UTC; nulo em chamado anterior à T15.")
    resolvedAt: datetime | None = None
    slaStatus: SlaStatusValue | None = Field(default=None, description="Estado de SLA calculado no instante da resposta.")


class TicketHistoryEntry(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_HISTORY[2]]})

    occurredAt: datetime
    action: Literal["OPENED", "ASSIGNED", "REASSIGNED", "ENTITLEMENT_CONFIRMED", "ENTITLEMENT_REJECTED", "RESOLVED"]
    fromStatus: str | None
    toStatus: str
    owner: str | None
    previousOwner: str | None
    actorRole: str | None
    slaStatus: SlaStatusValue | None
    correlationId: str


class ReconciledTicket(BaseModel):
    ticketId: UUID
    customerId: UUID
    contractId: UUID
    serviceCode: str
    category: str
    status: Literal["OPEN", "REJECTED_ENTITLEMENT"]
    priority: Literal["NORMAL", "HIGH"]
    slaHours: int | None
    dueAt: datetime | None
    openedAt: datetime | None = None
    resolvedAt: datetime | None = None
    slaStatus: SlaStatusValue | None = None


class PendingReconciliationResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_PENDING_SUMMARY]})

    confirmed: int = Field(description="Chamados que passaram a OPEN com SLA.")
    rejected: int = Field(description="Chamados que passaram a REJECTED_ENTITLEMENT.")
    remaining: int = Field(description="Chamados que continuam em PENDING_ENTITLEMENT após a execução.")
    contractsAvailable: bool = Field(description="false quando Contracts caiu durante o lote; repita a operação depois.")
    tickets: list[ReconciledTicket]


@router.get("/tickets", response_model=list[TicketDetailResponse], dependencies=[Depends(TICKET_READERS)])
def list_tickets(session: Session = Depends(get_session), service: TicketService = Depends(ticket_service)) -> list[dict]:
    return service.list_tickets(session)


@router.post(
    "/tickets/reconcile-pending",
    response_model=PendingReconciliationResponse,
    responses={503: {"description": "Contracts indisponível; nenhum chamado foi alterado."}},
)
def reconcile_pending(
    limit: int = Query(default=100, ge=1, le=PENDING_BATCH_MAX, description="Máximo de chamados pendentes consultados nesta execução."),
    principal: Principal = Depends(TICKET_RECONCILERS),
    session: Session = Depends(get_session),
    service: TicketService = Depends(ticket_service),
) -> dict:
    """Reconcilia explicitamente os chamados em PENDING_ENTITLEMENT depois que Contracts volta a responder."""
    return service.reconcile_pending(session, correlation_id_var.get(), acting_role(principal), limit)


@router.get("/tickets/{ticket_id}", response_model=TicketDetailResponse, responses=NOT_FOUND, dependencies=[Depends(TICKET_READERS)])
def get_ticket(ticket_id: UUID, session: Session = Depends(get_session), service: TicketService = Depends(ticket_service)) -> dict:
    return service.get(session, str(ticket_id))


@router.get(
    "/tickets/{ticket_id}/history",
    response_model=list[TicketHistoryEntry],
    responses={**NOT_FOUND, 200: {"content": {"application/json": {"example": EXAMPLE_HISTORY}}}},
    dependencies=[Depends(TICKET_READERS)],
)
def ticket_history(ticket_id: UUID, session: Session = Depends(get_session), service: TicketService = Depends(ticket_service)) -> list[dict]:
    """Histórico de abertura, atribuições, reconciliação e resolução, com papel e correlação de cada ação."""
    return service.history(session, str(ticket_id))


@router.post(
    "/tickets/{ticket_id}/assign",
    response_model=TicketDetailResponse,
    responses={**NOT_FOUND, 409: {"description": "Chamado resolvido ou rejeitado não pode ser atribuído."}},
)
def assign_ticket(
    ticket_id: UUID,
    body: AssignmentInput,
    principal: Principal = Depends(TICKET_AGENTS),
    session: Session = Depends(get_session),
    service: TicketService = Depends(ticket_service),
) -> dict:
    """Atribui ou reatribui o responsável; repetir o mesmo responsável não altera o histórico."""
    return service.assign(session, str(ticket_id), body.owner, correlation_id_var.get(), acting_role(principal))


@router.post(
    "/tickets/{ticket_id}/resolve",
    response_model=TicketDetailResponse,
    responses={
        **NOT_FOUND,
        200: {"headers": REPLAY_HEADER, "content": {"application/json": {"examples": {
            "resolved": {"summary": "Chamado resolvido dentro do SLA", "value": EXAMPLE_RESOLVED_DETAIL},
            "replayed": {"summary": "Resposta persistida da mesma chave; Idempotency-Replayed true", "value": EXAMPLE_RESOLVED_DETAIL},
        }}}},
        409: {"description": "Somente chamado aberto pode ser resolvido."},
    },
)
def resolve_ticket(
    ticket_id: UUID,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=100),
    principal: Principal = Depends(TICKET_AGENTS),
    session: Session = Depends(get_session),
    service: TicketService = Depends(ticket_service),
) -> dict:
    """Resolve chamado aberto; a mesma Idempotency-Key recupera a resposta original. Sem chave, preserva os conflitos v1."""
    result, replay = service.resolve(session, str(ticket_id), correlation_id_var.get(), acting_role(principal), idempotency_key)
    response.headers["Idempotency-Replayed"] = str(replay).lower()
    return result

