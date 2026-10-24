"""Schemas HTTP do contexto integration."""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from archcorp.api_examples import EXAMPLE_CUSTOMER_ID


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

