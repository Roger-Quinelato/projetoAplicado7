from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, model_validator


IDEMPOTENCY_KEY_MAX_LENGTH = 100
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]

EXAMPLE_CORRELATION_ID = "11111111-1111-4111-8111-111111111111"
EXAMPLE_CUSTOMER_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
EXAMPLE_CONTRACT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
EXAMPLE_CONTRACT_EVENT_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
EXAMPLE_TICKET_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"

EXAMPLE_CUSTOMER_RESPONSE = {
    "customerId": EXAMPLE_CUSTOMER_ID,
    "name": "Cliente Frota Localiza Ltda.",
    "email": "gestor.frota@cliente-sintetico.example.com",
    "eligible": True,
    "consentService": True,
    "active": True,
    "legacyId": "WEB-LOCALIZA-1001",
}

EXAMPLE_CONTRACT_DRAFT_RESPONSE = {
    "contractId": EXAMPLE_CONTRACT_ID,
    "customerId": EXAMPLE_CUSTOMER_ID,
    "serviceCode": "RENTAL-FLEX",
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
    "serviceCode": "RENTAL-FLEX",
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
                    "name": "Cliente Frota Localiza Ltda.",
                    "email": "gestor.frota@cliente-sintetico.example.com",
                    "eligible": True,
                    "consentService": True,
                    "legacyId": "WEB-LOCALIZA-1001",
                }
            ]
        }
    )

    name: Name
    email: EmailStr
    eligible: bool = True
    consentService: bool = True
    legacyId: str | None = Field(default=None, min_length=1, max_length=100)


class PartialUpdate(BaseModel):
    non_nullable: ClassVar[frozenset[str] | None] = None
    null_message: ClassVar[str] = "Campos não aceitam null"

    @model_validator(mode="after")
    def at_least_one_value(self):
        provided = self.model_dump(exclude_unset=True)
        if not provided:
            raise ValueError("Informe ao menos um campo para atualizar")
        checked = provided.keys() if self.non_nullable is None else self.non_nullable & provided.keys()
        if any(provided[field] is None for field in checked):
            raise ValueError(self.null_message)
        return self


class CustomerUpdate(PartialUpdate):
    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "Cliente Frota Sintética Atualizada", "consentService": True}]})
    null_message = "Campos do cliente não aceitam null"

    name: Name | None = None
    email: EmailStr | None = None
    eligible: bool | None = None
    consentService: bool | None = None


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
    category: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=3, max_length=2000)


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CustomerResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_CUSTOMER_RESPONSE]})

    customerId: UUID
    name: str
    email: EmailStr
    eligible: bool
    consentService: bool
    active: bool = True
    legacyId: str | None = None


class LegacyIdResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "entityType": "customer",
                    "globalId": EXAMPLE_CUSTOMER_ID,
                    "sourceSystem": "CRM",
                    "legacyId": "WEB-LOCALIZA-1001",
                }
            ]
        }
    )

    entityType: str
    globalId: UUID
    sourceSystem: str
    legacyId: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "UP", "database": "UP"}]})

    status: Literal["UP"]
    database: Literal["UP"] | None = None


class DemoStateResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{
        "customers": 3, "contracts": 2, "invoices": 1, "tickets": 1, "processes": 2, "legacyMappings": 3,
    }]})

    customers: int
    contracts: int
    invoices: int
    tickets: int
    processes: int
    legacyMappings: int


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


class DispatchResponse(BaseModel):
    processed: int
    failed: int


class FailureResponse(BaseModel):
    eventId: UUID
    eventType: str
    attempts: int
    reason: str | None
    correlationId: UUID


class ReprocessResponse(BaseModel):
    eventId: UUID
    status: Literal["PENDING"]


class AuditEntryResponse(BaseModel):
    occurredAt: datetime
    module: str
    operation: str
    result: str
    entityId: str | None
    details: dict[str, Any]


class OperationEventResponse(BaseModel):
    eventId: UUID
    eventType: str
    status: str
    attempts: int


class OperationTraceResponse(BaseModel):
    correlationId: UUID
    audit: list[AuditEntryResponse]
    events: list[OperationEventResponse]
