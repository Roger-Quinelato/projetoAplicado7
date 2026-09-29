from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.contracts.models import Contract, Reservation
from archcorp.contracts.service import ContractService
from archcorp.infrastructure.db import get_session
from archcorp.security import require_roles


router = APIRouter(prefix="/api/v1/contracts", tags=["Reservas e contratos"])


class ReservationInput(BaseModel):
    customerId: UUID
    vehicleGroup: str = Field(min_length=1, max_length=50)
    protectionCode: str = Field(min_length=1, max_length=50)
    serviceCode: str = Field(min_length=1, max_length=80)
    startsOn: date
    endsOn: date
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    billingCycle: Literal["MONTHLY", "ONCE"] = "MONTHLY"
    slaHours: int = Field(default=8, ge=1, le=720)

    @model_validator(mode="after")
    def dates_in_order(self):
        if self.endsOn < self.startsOn:
            raise ValueError("Fim da reserva anterior ao início")
        return self


def reservation_data(item: Reservation) -> dict:
    return {"reservationId": item.reservation_id, "customerId": item.customer_id,
            "vehicleGroup": item.vehicle_group, "protectionCode": item.protection_code,
            "serviceCode": item.service_code, "startsOn": item.starts_on.isoformat(),
            "endsOn": item.ends_on.isoformat(), "amount": float(item.amount),
            "currency": item.currency, "billingCycle": item.billing_cycle,
            "slaHours": item.sla_hours, "status": item.status, "contractId": item.contract_id}


@router.get("/reservations", dependencies=[Depends(require_roles("commercial", "contracts", "admin"))])
def list_reservations(customerId: UUID | None = None, session: Session = Depends(get_session)) -> list[dict]:
    query = select(Reservation).order_by(Reservation.starts_on.desc()).limit(200)
    if customerId:
        query = query.where(Reservation.customer_id == str(customerId))
    return [reservation_data(x) for x in session.scalars(query)]


@router.get("/reservations/{reservation_id}", dependencies=[Depends(require_roles("commercial", "contracts", "admin"))])
def get_reservation(reservation_id: UUID, session: Session = Depends(get_session)) -> dict:
    item = session.get(Reservation, str(reservation_id))
    if not item:
        raise HTTPException(404, "Reserva não encontrada")
    return reservation_data(item)


@router.get("", dependencies=[Depends(require_roles("commercial", "contracts", "finance", "support", "admin"))])
def list_contracts(customerId: UUID | None = None, session: Session = Depends(get_session)) -> list[dict]:
    query = select(Contract).order_by(Contract.starts_on.desc()).limit(200)
    if customerId:
        query = query.where(Contract.customer_id == str(customerId))
    return [ContractService.to_dict(x) for x in session.scalars(query)]


@router.get("/{contract_id}", dependencies=[Depends(require_roles("commercial", "contracts", "finance", "support", "admin"))])
def get_contract(contract_id: UUID, session: Session = Depends(get_session)) -> dict:
    item = session.get(Contract, str(contract_id))
    if not item:
        raise HTTPException(404, "Contrato não encontrado")
    return ContractService.to_dict(item)


@router.post("/{contract_id}/close", dependencies=[Depends(require_roles("contracts", "admin"))])
def close_contract(contract_id: UUID, session: Session = Depends(get_session)) -> dict:
    item = session.get(Contract, str(contract_id))
    if not item:
        raise HTTPException(404, "Contrato não encontrado")
    if item.status != "ACTIVE":
        raise HTTPException(409, "Somente contrato ativo pode ser encerrado")
    item.status = "CLOSED"
    reservation = session.scalar(select(Reservation).where(Reservation.contract_id == item.contract_id))
    if reservation:
        reservation.status = "CLOSED"
    session.commit()
    return ContractService.to_dict(item)
