"""Schemas HTTP do contexto support."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from archcorp.api_examples import EXAMPLE_CUSTOMER_ID, EXAMPLE_CONTRACT_ID


class TicketCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "customerId": EXAMPLE_CUSTOMER_ID,
                    "contractId": EXAMPLE_CONTRACT_ID,
                    "serviceCode": "RENTAL-FLEX",
                    "category": "OUTAGE",
                    "description": "Serviço indisponível durante a demonstração",
                }
            ]
        }
    )

    customerId: UUID
    contractId: UUID
    serviceCode: str
    category: str = Field(min_length=2, max_length=80, description="OUTAGE e SECURITY recebem prioridade alta; demais categorias, normal.")
    description: str = Field(min_length=3, max_length=2000, description="Relato da ocorrência, sem documento, cartão, telefone, placa ou e-mail.")


class TicketResponse(BaseModel):
    ticketId: UUID
    customerId: UUID
    contractId: UUID
    serviceCode: str
    category: str
    status: Literal["OPEN", "PENDING_ENTITLEMENT", "REJECTED_ENTITLEMENT"]
    priority: Literal["NORMAL", "HIGH"]
    slaHours: int | None
    dueAt: datetime | None
    openedAt: datetime | None = Field(default=None, description="Abertura em UTC; nulo em chamado anterior à T15.")
    resolvedAt: datetime | None = None
    slaStatus: Literal["PENDING", "WITHIN", "BREACHED", "MET", "NOT_APPLICABLE"] | None = Field(
        default=None, description="Estado de SLA no instante da resposta: PENDING sem elegibilidade, WITHIN ou BREACHED quando aberto, MET ou BREACHED quando resolvido.")

