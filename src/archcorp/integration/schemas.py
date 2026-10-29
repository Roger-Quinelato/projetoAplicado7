"""Schemas HTTP do contexto integration."""
from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

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


class OutboxSummaryResponse(BaseModel):
    pending: int
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



class EventInsight(BaseModel):
    eventType: str
    total: int
    published: int
    pending: int
    failed: int
    retried: int = Field(description="Publicados depois de pelo menos uma tentativa com falha.")
    maxAttempts: int


class DispatchLagInsight(BaseModel):
    consumer: str
    processed: int
    p50Seconds: float = Field(description="Mediana do tempo entre occurredAt e o processamento pelo consumidor.")
    p95Seconds: float
    maxSeconds: float


class AuditInsight(BaseModel):
    module: str
    operation: str
    result: str
    count: int


class IdempotencyInsight(BaseModel):
    operation: str
    count: int = Field(description="Chaves de idempotência registradas para a operação.")


class OperationalInsightsResponse(BaseModel):
    generatedAt: datetime
    events: list[EventInsight]
    dispatchLag: list[DispatchLagInsight]
    audit: list[AuditInsight]
    idempotencyKeys: list[IdempotencyInsight]
