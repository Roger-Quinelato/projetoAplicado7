from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.contracts.models import Contract, Reservation
from archcorp.contracts.service import ContractService, ReservationService
from archcorp.infrastructure.db import get_session
from archcorp.observability import correlation_id_var
from archcorp.schemas import EXAMPLE_CONTRACT_DRAFT_RESPONSE, EXAMPLE_CONTRACT_ID, EXAMPLE_CUSTOMER_ID, IDEMPOTENCY_KEY_MAX_LENGTH
from archcorp.security import require_roles


router = APIRouter(prefix="/api/v1/contracts", tags=["Reservas e contratos"])

# Matriz de autorização de reservas e contratos (docs/TDD_LOCALIZA.md).
RESERVATION_ACTORS = require_roles("commercial", "contracts", "admin")
CONTRACT_READERS = require_roles("commercial", "contracts", "finance", "support", "admin")
CONTRACT_OPERATORS = require_roles("contracts", "admin")


class _Services:
    contracts: ContractService | None = None
    reservations: ReservationService | None = None


def configure(contracts: ContractService) -> None:
    """Recebe o serviço montado pela composição da aplicação, sem importar o CRM."""
    _Services.contracts = contracts
    _Services.reservations = ReservationService(contracts)


def contract_service() -> ContractService:
    return _Services.contracts


def reservation_service() -> ReservationService:
    return _Services.reservations


EXAMPLE_RESERVATION_ID = "15151515-1515-4151-8151-151515151515"
EXAMPLE_RESERVATION_INPUT = {
    "customerId": EXAMPLE_CUSTOMER_ID,
    "vehicleGroup": "SUV-COMPACTO",
    "protectionCode": "BASICA",
    "serviceCode": "RENTAL-FLEX",
    "startsOn": "2027-01-04",
    "endsOn": "2027-01-08",
    "amount": 750.00,
    "currency": "BRL",
    "billingCycle": "ONCE",
    "slaHours": 8,
}
EXAMPLE_RESERVATION = {
    **EXAMPLE_RESERVATION_INPUT,
    "reservationId": EXAMPLE_RESERVATION_ID,
    "status": "REQUESTED",
    "contractId": None,
}
EXAMPLE_CONTRACT = {**EXAMPLE_CONTRACT_DRAFT_RESPONSE, "status": "ACTIVE"}


REPLAY_HEADERS = {
    "Idempotency-Replayed": {
        "description": "Retorna true quando a API reutiliza a resposta armazenada.",
        "schema": {"type": "string", "enum": ["true", "false"]},
    },
}


class ReservationInput(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_RESERVATION_INPUT]})

    customerId: UUID
    vehicleGroup: str = Field(min_length=1, max_length=50)
    protectionCode: str = Field(min_length=1, max_length=50)
    serviceCode: str = Field(min_length=1, max_length=80)
    startsOn: date
    endsOn: date
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(default="BRL", pattern="^[A-Z]{3}$")
    billingCycle: Literal["ONCE", "MONTHLY", "QUARTERLY", "YEARLY"] = "MONTHLY"
    slaHours: int = Field(default=8, ge=1, le=720)

    @model_validator(mode="after")
    def valid_period(self):
        if self.endsOn < self.startsOn:
            raise ValueError("Fim da reserva anterior ao início")
        if self.startsOn < date.today():
            raise ValueError("Início da reserva no passado")
        return self


class ContractCloseInput(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"endsOn": "2027-01-08", "reason": "Devolução do veículo"}]})

    endsOn: date | None = Field(default=None, description="Data de encerramento; padrão é a data atual ou o início do contrato, o que for posterior.")
    reason: str | None = Field(default=None, min_length=3, max_length=200)


class ReservationResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_RESERVATION]})

    reservationId: UUID
    customerId: UUID
    vehicleGroup: str
    protectionCode: str
    serviceCode: str
    startsOn: date
    endsOn: date
    amount: float
    currency: str
    billingCycle: str
    slaHours: int
    status: Literal["REQUESTED", "DRAFTED", "ACTIVE", "CLOSED", "CANCELLED"]
    contractId: UUID | None


class BillingResponse(BaseModel):
    amount: float
    currency: str
    cycle: str


class ContractResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_CONTRACT]})

    contractId: UUID
    customerId: UUID
    serviceCode: str
    startsOn: date
    endsOn: date | None = None
    billing: BillingResponse
    slaHours: int
    status: Literal["DRAFT", "ACTIVE", "CLOSED", "CANCELLED"]


class ReservationDraftResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{
        "reservationId": EXAMPLE_RESERVATION_ID,
        "contract": {**EXAMPLE_CONTRACT_DRAFT_RESPONSE, "contractId": EXAMPLE_CONTRACT_ID},
    }]})

    reservationId: UUID
    contract: ContractResponse


class ContractClosedResponse(ContractResponse):
    model_config = ConfigDict(json_schema_extra={"examples": [{**EXAMPLE_CONTRACT, "status": "CLOSED", "endsOn": "2027-01-08", "eventId": "18181818-1818-4181-8181-181818181818"}]})

    eventId: UUID


def set_replay(response: Response, replay: bool) -> None:
    response.headers["Idempotency-Replayed"] = str(replay).lower()


@router.post(
    "/reservations",
    status_code=201,
    response_model=ReservationResponse,
    responses={
        201: {"headers": REPLAY_HEADERS},
        404: {"description": "Cliente não encontrado."},
        409: {"description": "Idempotency-Key reutilizada com outra reserva."},
        422: {"description": "Cliente inelegível, sem consentimento, inativo ou período inválido."},
    },
    dependencies=[Depends(RESERVATION_ACTORS)],
)
def create_reservation(
    body: ReservationInput,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=IDEMPOTENCY_KEY_MAX_LENGTH,
                                         description="Opcional; quando informado, repetir a chamada devolve a mesma reserva."),
    session: Session = Depends(get_session),
    service: ReservationService = Depends(reservation_service),
) -> dict:
    result, replay = service.create(session, body.model_dump(mode="python") | {"customerId": str(body.customerId)}, idempotency_key, correlation_id_var.get())
    set_replay(response, replay)
    return result


@router.get("/reservations", response_model=list[ReservationResponse], dependencies=[Depends(RESERVATION_ACTORS)])
def list_reservations(customerId: UUID | None = None, session: Session = Depends(get_session)) -> list[dict]:
    query = select(Reservation).order_by(Reservation.starts_on.desc()).limit(200)
    if customerId:
        query = query.where(Reservation.customer_id == str(customerId))
    return [ReservationService.to_dict(x) for x in session.scalars(query)]


@router.get("/reservations/{reservation_id}", response_model=ReservationResponse, responses={404: {"description": "Reserva não encontrada."}}, dependencies=[Depends(RESERVATION_ACTORS)])
def get_reservation(reservation_id: UUID, session: Session = Depends(get_session)) -> dict:
    return ReservationService.to_dict(ReservationService.require(session, str(reservation_id)))


@router.post(
    "/reservations/{reservation_id}/draft",
    response_model=ReservationDraftResponse,
    responses={
        200: {"headers": REPLAY_HEADERS},
        404: {"description": "Reserva não encontrada."},
        409: {"description": "Reserva cancelada, Idempotency-Key reutilizada ou contrato já existente para cliente, serviço e início."},
        422: {"description": "Cliente inelegível, sem consentimento ou entrada inválida."},
    },
    dependencies=[Depends(RESERVATION_ACTORS)],
)
def draft_from_reservation(
    reservation_id: UUID,
    response: Response,
    idempotency_key: str = Header(alias="Idempotency-Key", max_length=IDEMPOTENCY_KEY_MAX_LENGTH),
    session: Session = Depends(get_session),
    service: ReservationService = Depends(reservation_service),
) -> dict:
    result, replay = service.draft(session, str(reservation_id), idempotency_key, correlation_id_var.get())
    set_replay(response, replay)
    return result


@router.post(
    "/reservations/{reservation_id}/cancel",
    response_model=ReservationResponse,
    responses={404: {"description": "Reserva não encontrada."}, 409: {"description": "Reserva ativa ou encerrada não pode ser cancelada."}},
    dependencies=[Depends(RESERVATION_ACTORS)],
)
def cancel_reservation(reservation_id: UUID, session: Session = Depends(get_session),
                       service: ReservationService = Depends(reservation_service)) -> dict:
    """Cancela reserva solicitada ou com rascunho; o rascunho vinculado também é cancelado."""
    return service.cancel(session, str(reservation_id), correlation_id_var.get())


@router.get("", response_model=list[ContractResponse], dependencies=[Depends(CONTRACT_READERS)])
def list_contracts(customerId: UUID | None = None, session: Session = Depends(get_session)) -> list[dict]:
    query = select(Contract).order_by(Contract.starts_on.desc()).limit(200)
    if customerId:
        query = query.where(Contract.customer_id == str(customerId))
    return [ContractService.to_dict(x) for x in session.scalars(query)]


@router.get("/{contract_id}", response_model=ContractResponse, responses={404: {"description": "Contrato não encontrado."}}, dependencies=[Depends(CONTRACT_READERS)])
def get_contract(contract_id: UUID, session: Session = Depends(get_session)) -> dict:
    return ContractService.to_dict(ContractService.require(session, str(contract_id)))


@router.post(
    "/{contract_id}/close",
    response_model=ContractClosedResponse,
    responses={
        200: {"headers": REPLAY_HEADERS},
        404: {"description": "Contrato não encontrado."},
        409: {"description": "Somente contrato ativo pode ser encerrado."},
        422: {"description": "Data de encerramento anterior ao início ou entrada inválida."},
    },
    dependencies=[Depends(CONTRACT_OPERATORS)],
)
def close_contract(
    contract_id: UUID,
    response: Response,
    body: ContractCloseInput | None = None,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=IDEMPOTENCY_KEY_MAX_LENGTH,
                                         description="Opcional; com a chave, repetir o encerramento devolve a mesma resposta."),
    session: Session = Depends(get_session),
    service: ContractService = Depends(contract_service),
) -> dict:
    """Encerra contrato ativo, encerra a reserva vinculada e publica ContractClosed.v1."""
    data = (body or ContractCloseInput()).model_dump()
    result, replay = service.close(session, str(contract_id), data, idempotency_key, correlation_id_var.get())
    set_replay(response, replay)
    return result
