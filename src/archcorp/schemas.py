from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


EXAMPLE_CORRELATION_ID = "11111111-1111-4111-8111-111111111111"
EXAMPLE_CUSTOMER_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
EXAMPLE_CONTRACT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
EXAMPLE_CONTRACT_EVENT_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
EXAMPLE_TICKET_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"

EXAMPLE_CUSTOMER_RESPONSE = {
    "customerId": EXAMPLE_CUSTOMER_ID,
    "name": "Empresa Exemplo Ltda.",
    "email": "contato@empresa-exemplo.test",
    "eligible": True,
}

EXAMPLE_CONTRACT_DRAFT_RESPONSE = {
    "contractId": EXAMPLE_CONTRACT_ID,
    "customerId": EXAMPLE_CUSTOMER_ID,
    "serviceCode": "SUPPORT-PREMIUM",
    "startsOn": "2026-10-01",
    "billing": {
        "amount": 2500.00,
        "currency": "BRL",
        "cycle": "MONTHLY",
    },
    "slaHours": 8,
    "status": "DRAFT",
}

EXAMPLE_CONTRACT_ACTIVATED_RESPONSE = {
    **EXAMPLE_CONTRACT_DRAFT_RESPONSE,
    "status": "ACTIVE",
    "eventId": EXAMPLE_CONTRACT_EVENT_ID,
}

EXAMPLE_TICKET_RESPONSE = {
    "ticketId": EXAMPLE_TICKET_ID,
    "customerId": EXAMPLE_CUSTOMER_ID,
    "contractId": EXAMPLE_CONTRACT_ID,
    "serviceCode": "SUPPORT-PREMIUM",
    "category": "OUTAGE",
    "status": "OPEN",
    "priority": "HIGH",
    "slaHours": 8,
    "dueAt": "2026-10-01T18:10:00Z",
}

EXAMPLE_PENDING_TICKET_RESPONSE = {
    **EXAMPLE_TICKET_RESPONSE,
    "category": "QUESTION",
    "status": "PENDING_ENTITLEMENT",
    "priority": "NORMAL",
    "slaHours": None,
    "dueAt": None,
}


class CustomerCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Empresa Exemplo Ltda.",
                    "email": "contato@empresa-exemplo.test",
                    "eligible": True,
                    "consentService": True,
                    "legacyId": "CRM-1001",
                }
            ]
        }
    )

    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    eligible: bool = True
    consentService: bool = True
    legacyId: str | None = Field(default=None, max_length=100)


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    eligible: bool | None = None
    consentService: bool | None = None


class Billing(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(pattern="^[A-Z]{3}$")
    cycle: str = Field(pattern="^(MONTHLY|QUARTERLY|YEARLY)$")


class ContractDraftCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "customerId": EXAMPLE_CUSTOMER_ID,
                    "serviceCode": "SUPPORT-PREMIUM",
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

    customerId: str
    serviceCode: str = Field(min_length=2, max_length=80)
    startsOn: date
    billing: Billing
    slaHours: int = Field(default=8, ge=1, le=720)


class TicketCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "customerId": EXAMPLE_CUSTOMER_ID,
                    "contractId": EXAMPLE_CONTRACT_ID,
                    "serviceCode": "SUPPORT-PREMIUM",
                    "category": "OUTAGE",
                    "description": "Serviço indisponível durante a demonstração",
                }
            ]
        }
    )

    customerId: str
    contractId: str
    serviceCode: str
    category: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=3, max_length=2000)


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
