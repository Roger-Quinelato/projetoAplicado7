"""Schemas HTTP do contexto contracts."""
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from archcorp.api_examples import EXAMPLE_CUSTOMER_ID


class Billing(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(pattern="^[A-Z]{3}$")
    cycle: str = Field(pattern="^(ONCE|MONTHLY|QUARTERLY|YEARLY)$")


class ContractDraftCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "customerId": EXAMPLE_CUSTOMER_ID,
                    "serviceCode": "RENTAL-FLEX",
                    "startsOn": "2026-10-01",
                    "billing": {
                        "amount": 2500.00,
                        "currency": "BRL",
                        "cycle": "MONTHLY",
                    },
                    "slaHours": 8,
                }
            ]
        }
    )

    customerId: UUID
    serviceCode: str = Field(min_length=2, max_length=80)
    startsOn: date
    billing: Billing
    slaHours: int = Field(default=8, ge=1, le=720)


class ContractDraftResponse(BaseModel):
    contractId: UUID
    customerId: UUID
    serviceCode: str
    startsOn: date
    endsOn: date | None = None
    billing: Billing
    slaHours: int
    status: Literal["DRAFT"]


class ContractActivationResponse(BaseModel):
    contractId: UUID
    customerId: UUID
    serviceCode: str
    startsOn: date
    endsOn: date | None = None
    billing: Billing
    slaHours: int
    status: Literal["ACTIVE"]
    eventId: UUID


class EntitlementResponse(BaseModel):
    eligible: bool
    slaHours: int | None

