"""Compatibilidade dos imports públicos anteriores; schemas pertencem a cada módulo."""
from typing import Literal
from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


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


from archcorp.api_examples import IDEMPOTENCY_KEY_MAX_LENGTH, Name, EXAMPLE_CORRELATION_ID, EXAMPLE_CUSTOMER_ID, EXAMPLE_CONTRACT_ID, EXAMPLE_CONTRACT_EVENT_ID, EXAMPLE_TICKET_ID, EXAMPLE_CUSTOMER_RESPONSE, EXAMPLE_CONTRACT_DRAFT_RESPONSE, EXAMPLE_CONTRACT_ACTIVATED_RESPONSE, EXAMPLE_TICKET_RESPONSE, EXAMPLE_PENDING_TICKET_RESPONSE
from archcorp.crm.schemas import CustomerCreate, CustomerUpdate, CustomerResponse
from archcorp.contracts.schemas import Billing, ContractDraftCreate, ContractDraftResponse, ContractActivationResponse, EntitlementResponse
from archcorp.support.schemas import TicketCreate, TicketResponse
from archcorp.integration.schemas import LegacyIdResponse, DispatchResponse, FailureResponse, ReprocessResponse, AuditEntryResponse, OperationEventResponse, OperationTraceResponse

__all__ = ['IDEMPOTENCY_KEY_MAX_LENGTH', 'Name', 'EXAMPLE_CORRELATION_ID', 'EXAMPLE_CUSTOMER_ID', 'EXAMPLE_CONTRACT_ID', 'EXAMPLE_CONTRACT_EVENT_ID', 'EXAMPLE_TICKET_ID', 'EXAMPLE_CUSTOMER_RESPONSE', 'EXAMPLE_CONTRACT_DRAFT_RESPONSE', 'EXAMPLE_CONTRACT_ACTIVATED_RESPONSE', 'EXAMPLE_TICKET_RESPONSE', 'EXAMPLE_PENDING_TICKET_RESPONSE', 'CustomerCreate', 'CustomerUpdate', 'CustomerResponse', 'Billing', 'ContractDraftCreate', 'ContractDraftResponse', 'ContractActivationResponse', 'EntitlementResponse', 'TicketCreate', 'TicketResponse', 'LegacyIdResponse', 'DispatchResponse', 'FailureResponse', 'ReprocessResponse', 'AuditEntryResponse', 'OperationEventResponse', 'OperationTraceResponse', 'ApiModel', 'HealthResponse', 'DemoStateResponse']
