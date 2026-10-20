from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from archcorp.infrastructure.db import get_session
from archcorp.observability import correlation_id_var
from archcorp.security import require_roles
from archcorp.api_docs import CORRELATION_REQUEST_PARAMETER, DISPATCH_RESPONSES, OUTBOX_SUMMARY_RESPONSES, FAILURE_LIST_RESPONSES, REPROCESS_RESPONSES, OPERATION_TRACE_RESPONSES, COMMON_API_ERRORS
from archcorp.errors import problem_content, problem_example
from archcorp.integration.schemas import DispatchResponse, OutboxSummaryResponse, FailureResponse, ReprocessResponse, LegacyIdResponse, OperationTraceResponse
from archcorp.integration.models import AuditLog, OutboxEvent
from archcorp.integration.service import EventDispatcher, LegacyIdService, audit
router = APIRouter(tags=["Integração"])
_dispatcher: EventDispatcher | None = None

def configure(dispatcher: EventDispatcher) -> None:
    global _dispatcher
    _dispatcher = dispatcher

def dispatcher_service() -> EventDispatcher:
    return _dispatcher


@router.post(
    "/api/v1/integration/outbox/dispatch",
    response_model=DispatchResponse,
    dependencies=[Depends(require_roles("operations", "admin"))],
    responses=DISPATCH_RESPONSES,
    openapi_extra={"parameters": [CORRELATION_REQUEST_PARAMETER]},
)
def dispatch_outbox(session: Session = Depends(get_session), dispatcher: EventDispatcher = Depends(dispatcher_service)) -> dict:
    return dispatcher.dispatch_pending(session)


@router.get(
    "/api/v1/integration/outbox/summary",
    response_model=OutboxSummaryResponse,
    dependencies=[Depends(require_roles("operations", "admin"))],
    responses=OUTBOX_SUMMARY_RESPONSES,
    openapi_extra={"parameters": [CORRELATION_REQUEST_PARAMETER]},
)
def outbox_summary(session: Session = Depends(get_session)) -> dict:
    counts = dict(session.execute(select(OutboxEvent.status, func.count()).where(OutboxEvent.status.in_(("PENDING", "FAILED"))).group_by(OutboxEvent.status)).all())
    return {"pending": counts.get("PENDING", 0), "failed": counts.get("FAILED", 0)}


@router.get(
    "/api/v1/integration/failures",
    response_model=list[FailureResponse],
    dependencies=[Depends(require_roles("operations", "admin"))],
    responses=FAILURE_LIST_RESPONSES,
    openapi_extra={"parameters": [CORRELATION_REQUEST_PARAMETER]},
)
def list_failures(session: Session = Depends(get_session)) -> list[dict]:
    failures = session.scalars(select(OutboxEvent).where(OutboxEvent.status == "FAILED")).all()
    return [{"eventId": e.event_id, "eventType": e.event_type, "attempts": e.attempts, "reason": e.last_error, "correlationId": e.correlation_id} for e in failures]


@router.post(
    "/api/v1/integration/failures/{event_id}/reprocess",
    response_model=ReprocessResponse,
    dependencies=[Depends(require_roles("operations", "admin"))],
    responses=REPROCESS_RESPONSES,
    openapi_extra={"parameters": [CORRELATION_REQUEST_PARAMETER]},
)
def reprocess(event_id: UUID, session: Session = Depends(get_session)) -> dict:
    event = session.get(OutboxEvent, str(event_id))
    if not event or event.status != "FAILED":
        raise HTTPException(status_code=404, detail="Falha não encontrada")
    event.status = "PENDING"
    event.last_error = None
    audit(session, correlation_id_var.get(), "integration", "reprocess_event", "scheduled", event.event_id, previousAttempts=event.attempts)
    event.attempts = 0
    session.commit()
    return {"eventId": event.event_id, "status": "PENDING"}


@router.get(
    "/api/v1/integration/legacy-ids/{source_system}/{legacy_id}",
    response_model=LegacyIdResponse,
    dependencies=[Depends(require_roles("commercial", "operations", "admin"))],
    responses={
        **COMMON_API_ERRORS,
        404: {
            "description": "Identificador legado não mapeado.",
            "content": problem_content(problem_example(404, "Identificador legado não encontrado", "/api/v1/integration/legacy-ids/CRM/WEB-LOCALIZA-9999")),
        },
    },
    openapi_extra={"parameters": [CORRELATION_REQUEST_PARAMETER]},
)
def resolve_legacy_id(source_system: str, legacy_id: str, session: Session = Depends(get_session)) -> dict:
    mapping = LegacyIdService.resolve(session, source_system, legacy_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="Identificador legado não encontrado")
    return LegacyIdService.as_dict(mapping)


@router.get(
    "/api/v1/operations/{correlation_id}",
    response_model=OperationTraceResponse,
    dependencies=[Depends(require_roles("operations", "admin"))],
    responses=OPERATION_TRACE_RESPONSES,
    openapi_extra={"parameters": [CORRELATION_REQUEST_PARAMETER]},
)
def operation_trace(correlation_id: UUID, session: Session = Depends(get_session)) -> dict:
    correlation_value = str(correlation_id)
    entries = session.scalars(select(AuditLog).where(AuditLog.correlation_id == correlation_value).order_by(AuditLog.occurred_at)).all()
    events = session.scalars(select(OutboxEvent).where(OutboxEvent.correlation_id == correlation_value).order_by(OutboxEvent.occurred_at)).all()
    return {"correlationId": correlation_value, "audit": [{"occurredAt": a.occurred_at, "module": a.module, "operation": a.operation, "result": a.result, "entityId": a.entity_id, "details": a.details} for a in entries], "events": [{"eventId": e.event_id, "eventType": e.event_type, "status": e.status, "attempts": e.attempts} for e in events]}

