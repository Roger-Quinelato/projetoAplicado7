from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from archcorp.contracts.models import Contract
from archcorp.contracts.service import ContractService
from archcorp.crm.models import Customer
from archcorp.crm.service import CustomerService
from archcorp.finance.models import Invoice
from archcorp.finance.service import handle_contract_activated as finance_contract_activated
from archcorp.infrastructure.db import Base, engine, get_session
from archcorp.integration.models import AuditLog, LegacyIdMapping, OutboxEvent
from archcorp.integration.service import EventDispatcher, audit
from archcorp.observability import correlation_id_var, logger, metrics_middleware, render_metrics
from archcorp.schemas import (
    EXAMPLE_CONTRACT_ACTIVATED_RESPONSE,
    EXAMPLE_CONTRACT_DRAFT_RESPONSE,
    EXAMPLE_CONTRACT_EVENT_ID,
    EXAMPLE_CONTRACT_ID,
    EXAMPLE_CORRELATION_ID,
    EXAMPLE_CUSTOMER_RESPONSE,
    EXAMPLE_PENDING_TICKET_RESPONSE,
    EXAMPLE_TICKET_RESPONSE,
    ContractActivationResponse,
    ContractDraftCreate,
    ContractDraftResponse,
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
    DispatchResponse,
    EntitlementResponse,
    FailureResponse,
    OperationTraceResponse,
    ReprocessResponse,
    TicketCreate,
    TicketResponse,
)
from archcorp.security import require_roles
from archcorp.support.models import Ticket
from archcorp.support.service import TicketService
from archcorp.workflow.models import ProcessInstance
from archcorp.workflow.service import handle_contract_activated as workflow_contract_activated, handle_ticket_opened


CORRELATION_REQUEST_PARAMETER = {
    "name": "X-Correlation-ID",
    "in": "header",
    "required": False,
    "description": "UUID de correlação. A API gera um UUID quando o cabeçalho é omitido.",
    "schema": {"type": "string", "format": "uuid"},
    "example": EXAMPLE_CORRELATION_ID,
}
CORRELATION_RESPONSE_HEADER = {
    "description": "UUID usado para correlacionar a requisição, os logs e os eventos.",
    "schema": {"type": "string", "format": "uuid"},
    "example": EXAMPLE_CORRELATION_ID,
}
IDEMPOTENCY_RESPONSE_HEADERS = {
    "X-Correlation-ID": CORRELATION_RESPONSE_HEADER,
    "Idempotency-Replayed": {
        "description": "Retorna true quando a API reutiliza a resposta armazenada.",
        "schema": {"type": "string", "enum": ["true", "false"]},
        "example": "false",
    },
}
COMMON_API_ERRORS = {
    400: {
        "description": "Cabeçalho de correlação inválido.",
        "content": {
            "application/json": {
                "example": {"detail": "X-Correlation-ID deve ser UUID"}
            }
        },
    },
    401: {
        "description": "Token ausente ou inválido.",
        "content": {
            "application/json": {"example": {"detail": "Token ausente ou inválido"}}
        },
    },
    403: {
        "description": "Papel sem permissão para a operação.",
        "content": {
            "application/json": {
                "example": {"detail": "Papel sem permissão para esta operação"}
            }
        },
    },
}
CUSTOMER_CREATE_RESPONSES = {
    **COMMON_API_ERRORS,
    201: {
        "description": "Cliente criado no CRM com identificador global.",
        "headers": {"X-Correlation-ID": CORRELATION_RESPONSE_HEADER},
        "content": {"application/json": {"example": EXAMPLE_CUSTOMER_RESPONSE}},
    },
}
CONTRACT_DRAFT_RESPONSES = {
    **COMMON_API_ERRORS,
    201: {
        "description": "Rascunho criado ou resposta idempotente recuperada.",
        "headers": IDEMPOTENCY_RESPONSE_HEADERS,
        "content": {
            "application/json": {
                "examples": {
                    "created": {
                        "summary": "Rascunho criado",
                        "value": EXAMPLE_CONTRACT_DRAFT_RESPONSE,
                    },
                    "replayed": {
                        "summary": "Resposta recuperada com Idempotency-Replayed true",
                        "value": EXAMPLE_CONTRACT_DRAFT_RESPONSE,
                    },
                }
            }
        },
    },
    422: {
        "description": "Entrada inválida ou cliente inexistente, inelegível ou sem consentimento.",
        "content": {
            "application/json": {
                "examples": {
                    "businessRule": {
                        "summary": "Cliente não pode originar contrato",
                        "value": {"detail": "Cliente inexistente ou inelegível"},
                    },
                    "validation": {
                        "summary": "Corpo da requisição inválido",
                        "value": {
                            "detail": [
                                {
                                    "type": "uuid_parsing",
                                    "loc": ["body", "customerId"],
                                    "msg": "Input should be a valid UUID",
                                    "input": "not-a-uuid",
                                }
                            ]
                        },
                    },
                }
            }
        },
    },
}
CONTRACT_ACTIVATION_RESPONSES = {
    **COMMON_API_ERRORS,
    200: {
        "description": "Contrato ativado ou resposta idempotente recuperada.",
        "headers": IDEMPOTENCY_RESPONSE_HEADERS,
        "content": {
            "application/json": {
                "examples": {
                    "activated": {
                        "summary": "Contrato ativado e evento gravado na outbox",
                        "value": EXAMPLE_CONTRACT_ACTIVATED_RESPONSE,
                    },
                    "replayed": {
                        "summary": "Resposta recuperada com Idempotency-Replayed true",
                        "value": EXAMPLE_CONTRACT_ACTIVATED_RESPONSE,
                    },
                }
            }
        },
    },
    404: {
        "description": "Contrato não encontrado.",
        "content": {
            "application/json": {"example": {"detail": "Contrato não encontrado"}}
        },
    },
}
ENTITLEMENT_RESPONSES = {
    **COMMON_API_ERRORS,
    200: {
        "description": "Elegibilidade e SLA do contrato.",
        "headers": {"X-Correlation-ID": CORRELATION_RESPONSE_HEADER},
        "content": {
            "application/json": {
                "examples": {
                    "eligible": {
                        "summary": "Contrato elegível",
                        "value": {"eligible": True, "slaHours": 8},
                    },
                    "notEligible": {
                        "summary": "Contrato não elegível",
                        "value": {"eligible": False, "slaHours": None},
                    },
                }
            }
        },
    },
}
TICKET_RESPONSES = {
    **COMMON_API_ERRORS,
    201: {
        "description": "Chamado criado ou resposta idempotente recuperada.",
        "headers": IDEMPOTENCY_RESPONSE_HEADERS,
        "content": {
            "application/json": {
                "examples": {
                    "open": {
                        "summary": "Chamado elegível aberto",
                        "value": EXAMPLE_TICKET_RESPONSE,
                    },
                    "pending": {
                        "summary": "Chamado pendente por indisponibilidade de Contracts",
                        "value": EXAMPLE_PENDING_TICKET_RESPONSE,
                    },
                    "replayed": {
                        "summary": "Resposta recuperada com Idempotency-Replayed true",
                        "value": EXAMPLE_TICKET_RESPONSE,
                    },
                }
            }
        },
    },
    422: {
        "description": "Entrada inválida ou contrato, serviço ou cliente sem elegibilidade.",
        "content": {
            "application/json": {
                "examples": {
                    "businessRule": {
                        "summary": "Contrato sem elegibilidade",
                        "value": {
                            "detail": "Contrato, serviço ou cliente sem elegibilidade"
                        },
                    },
                    "validation": {
                        "summary": "Corpo da requisição inválido",
                        "value": {
                            "detail": [
                                {
                                    "type": "uuid_parsing",
                                    "loc": ["body", "contractId"],
                                    "msg": "Input should be a valid UUID",
                                    "input": "not-a-uuid",
                                }
                            ]
                        },
                    },
                }
            }
        },
    },
}
RECONCILIATION_RESPONSES = {
    **COMMON_API_ERRORS,
    200: {
        "description": "Chamado reconciliado com a elegibilidade atual.",
        "headers": {"X-Correlation-ID": CORRELATION_RESPONSE_HEADER},
        "content": {
            "application/json": {
                "examples": {
                    "open": {
                        "summary": "Elegibilidade confirmada",
                        "value": EXAMPLE_TICKET_RESPONSE,
                    },
                    "rejected": {
                        "summary": "Elegibilidade rejeitada",
                        "value": {
                            **EXAMPLE_PENDING_TICKET_RESPONSE,
                            "status": "REJECTED_ENTITLEMENT",
                        },
                    },
                }
            }
        },
    },
    404: {
        "description": "Chamado não encontrado.",
        "content": {
            "application/json": {"example": {"detail": "Chamado não encontrado"}}
        },
    },
}
DISPATCH_RESPONSES = {
    **COMMON_API_ERRORS,
    200: {
        "description": "Resumo do despacho dos eventos pendentes.",
        "headers": {"X-Correlation-ID": CORRELATION_RESPONSE_HEADER},
        "content": {
            "application/json": {"example": {"processed": 1, "failed": 0}}
        },
    },
}
FAILURE_LIST_RESPONSES = {
    **COMMON_API_ERRORS,
    200: {
        "description": "Eventos que atingiram o limite de tentativas.",
        "headers": {"X-Correlation-ID": CORRELATION_RESPONSE_HEADER},
        "content": {
            "application/json": {
                "example": [
                    {
                        "eventId": EXAMPLE_CONTRACT_EVENT_ID,
                        "eventType": "ContractActivated.v1",
                        "attempts": 3,
                        "reason": "dependência simulada indisponível",
                        "correlationId": EXAMPLE_CORRELATION_ID,
                    }
                ]
            }
        },
    },
}
REPROCESS_RESPONSES = {
    **COMMON_API_ERRORS,
    200: {
        "description": "Evento recolocado em PENDING para novo despacho.",
        "headers": {"X-Correlation-ID": CORRELATION_RESPONSE_HEADER},
        "content": {
            "application/json": {
                "example": {
                    "eventId": EXAMPLE_CONTRACT_EVENT_ID,
                    "status": "PENDING",
                }
            }
        },
    },
    404: {
        "description": "Evento com falha não encontrado.",
        "content": {
            "application/json": {"example": {"detail": "Falha não encontrada"}}
        },
    },
}
OPERATION_TRACE_RESPONSES = {
    **COMMON_API_ERRORS,
    200: {
        "description": "Auditoria e eventos vinculados ao correlationId.",
        "headers": {"X-Correlation-ID": CORRELATION_RESPONSE_HEADER},
        "content": {
            "application/json": {
                "example": {
                    "correlationId": EXAMPLE_CORRELATION_ID,
                    "audit": [
                        {
                            "occurredAt": "2026-10-01T10:00:00Z",
                            "module": "contracts",
                            "operation": "activate_contract",
                            "result": "success",
                            "entityId": EXAMPLE_CONTRACT_ID,
                            "details": {},
                        }
                    ],
                    "events": [
                        {
                            "eventId": EXAMPLE_CONTRACT_EVENT_ID,
                            "eventType": "ContractActivated.v1",
                            "status": "PUBLISHED",
                            "attempts": 0,
                        }
                    ],
                }
            }
        },
    },
}


customers = CustomerService()
contracts = ContractService(customers)
tickets = TicketService(contracts)
dispatcher = EventDispatcher({
    "ContractActivated.v1": [("finance", finance_contract_activated), ("workflow-onboarding", workflow_contract_activated)],
    "TicketOpened.v1": [("workflow-ticket-resolution", handle_ticket_opened)],
    "CustomerUpdated.v1": [("contracts-customer-projection", ContractService.apply_customer_update)],
})


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="ArchCorp Integração Cenário 4", version="1.0.0", description="API demonstrativa para CRM, contratos, financeiro, atendimento, workflow e integração.", lifespan=lifespan)
app.middleware("http")(metrics_middleware)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    supplied = request.headers.get("X-Correlation-ID")
    try:
        correlation_id = str(UUID(supplied)) if supplied else str(uuid4())
    except ValueError:
        return Response(content='{"detail":"X-Correlation-ID deve ser UUID"}', status_code=400, media_type="application/json")
    token = correlation_id_var.set(correlation_id)
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        logger.info("Requisição concluída", extra={"operation": request.url.path, "result": response.status_code})
        return response
    finally:
        correlation_id_var.reset(token)


@app.get("/health/live", tags=["Operação"])
def live() -> dict:
    return {"status": "UP"}


@app.get("/health/ready", tags=["Operação"])
def ready(session: Session = Depends(get_session)) -> dict:
    try:
        session.execute(text("SELECT 1"))
        return {"status": "UP", "database": "UP"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Banco indisponível") from exc


@app.get("/metrics", response_class=PlainTextResponse, tags=["Operação"])
def metrics() -> str:
    return render_metrics()


@app.post(
    "/api/v1/crm/customers",
    status_code=201,
    response_model=CustomerResponse,
    tags=["CRM"],
    dependencies=[Depends(require_roles("commercial", "admin"))],
    responses=CUSTOMER_CREATE_RESPONSES,
    openapi_extra={"parameters": [CORRELATION_REQUEST_PARAMETER]},
)
def create_customer(body: CustomerCreate, session: Session = Depends(get_session)) -> dict:
    customer = customers.create(session, body.model_dump(mode="json"), correlation_id_var.get())
    return {"customerId": customer.customer_id, "name": customer.name, "email": customer.email, "eligible": customer.eligible}


@app.patch("/api/v1/crm/customers/{customer_id}", tags=["CRM"], dependencies=[Depends(require_roles("commercial", "admin"))])
def update_customer(customer_id: UUID, body: CustomerUpdate, session: Session = Depends(get_session)) -> dict:
    customer = customers.update(session, str(customer_id), body.model_dump(exclude_unset=True, mode="json"), correlation_id_var.get())
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return {"customerId": customer.customer_id, "name": customer.name, "email": customer.email}


@app.post(
    "/api/v1/contracts/drafts",
    status_code=201,
    response_model=ContractDraftResponse,
    tags=["Contratos"],
    dependencies=[Depends(require_roles("commercial", "contracts", "admin"))],
    responses=CONTRACT_DRAFT_RESPONSES,
    openapi_extra={"parameters": [CORRELATION_REQUEST_PARAMETER]},
)
def create_contract_draft(
    body: ContractDraftCreate,
    response: Response,
    idempotency_key: str = Header(
        alias="Idempotency-Key", examples=["demo-contract-001"]
    ),
    session: Session = Depends(get_session),
) -> dict:
    draft_data = body.model_dump()
    draft_data["customerId"] = str(draft_data["customerId"])
    try:
        result, replay = contracts.create_draft(session, draft_data, idempotency_key, correlation_id_var.get())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response.headers["Idempotency-Replayed"] = str(replay).lower()
    return result


@app.post(
    "/api/v1/contracts/{contract_id}/activate",
    response_model=ContractActivationResponse,
    tags=["Contratos"],
    dependencies=[Depends(require_roles("contracts", "admin"))],
    responses=CONTRACT_ACTIVATION_RESPONSES,
    openapi_extra={"parameters": [CORRELATION_REQUEST_PARAMETER]},
)
def activate_contract(
    contract_id: UUID,
    response: Response,
    idempotency_key: str = Header(
        alias="Idempotency-Key", examples=["demo-activate-001"]
    ),
    session: Session = Depends(get_session),
) -> dict:
    try:
        result, replay = contracts.activate(session, str(contract_id), idempotency_key, correlation_id_var.get())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    response.headers["Idempotency-Replayed"] = str(replay).lower()
    return result


@app.get(
    "/api/v1/contracts/{contract_id}/entitlement",
    response_model=EntitlementResponse,
    tags=["Contratos"],
    dependencies=[Depends(require_roles("support", "admin"))],
    responses=ENTITLEMENT_RESPONSES,
    openapi_extra={"parameters": [CORRELATION_REQUEST_PARAMETER]},
)
def entitlement(contract_id: UUID, customerId: UUID, serviceCode: str, session: Session = Depends(get_session)) -> dict:
    return contracts.entitlement(session, str(contract_id), str(customerId), serviceCode)


@app.post(
    "/api/v1/support/tickets",
    status_code=201,
    response_model=TicketResponse,
    tags=["Atendimento"],
    dependencies=[Depends(require_roles("support", "admin"))],
    responses=TICKET_RESPONSES,
    openapi_extra={"parameters": [CORRELATION_REQUEST_PARAMETER]},
)
def open_ticket(
    body: TicketCreate,
    response: Response,
    idempotency_key: str = Header(
        alias="Idempotency-Key", examples=["demo-ticket-001"]
    ),
    session: Session = Depends(get_session),
) -> dict:
    ticket_data = body.model_dump(mode="json")
    try:
        result, replay = tickets.open(session, ticket_data, idempotency_key, correlation_id_var.get())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response.headers["Idempotency-Replayed"] = str(replay).lower()
    return result


@app.post(
    "/api/v1/support/tickets/{ticket_id}/reconcile",
    response_model=TicketResponse,
    tags=["Atendimento"],
    dependencies=[Depends(require_roles("support", "operations", "admin"))],
    responses=RECONCILIATION_RESPONSES,
    openapi_extra={"parameters": [CORRELATION_REQUEST_PARAMETER]},
)
def reconcile_ticket(ticket_id: UUID, session: Session = Depends(get_session)) -> dict:
    try:
        return tickets.reconcile(session, str(ticket_id), correlation_id_var.get())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/api/v1/integration/outbox/dispatch",
    response_model=DispatchResponse,
    tags=["Integração"],
    dependencies=[Depends(require_roles("operations", "admin"))],
    responses=DISPATCH_RESPONSES,
    openapi_extra={"parameters": [CORRELATION_REQUEST_PARAMETER]},
)
def dispatch_outbox(session: Session = Depends(get_session)) -> dict:
    return dispatcher.dispatch_pending(session)


@app.get(
    "/api/v1/integration/failures",
    response_model=list[FailureResponse],
    tags=["Integração"],
    dependencies=[Depends(require_roles("operations", "admin"))],
    responses=FAILURE_LIST_RESPONSES,
    openapi_extra={"parameters": [CORRELATION_REQUEST_PARAMETER]},
)
def list_failures(session: Session = Depends(get_session)) -> list[dict]:
    failures = session.scalars(select(OutboxEvent).where(OutboxEvent.status == "FAILED")).all()
    return [{"eventId": e.event_id, "eventType": e.event_type, "attempts": e.attempts, "reason": e.last_error, "correlationId": e.correlation_id} for e in failures]


@app.post(
    "/api/v1/integration/failures/{event_id}/reprocess",
    response_model=ReprocessResponse,
    tags=["Integração"],
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
    session.commit()
    return {"eventId": event.event_id, "status": "PENDING"}


@app.get(
    "/api/v1/operations/{correlation_id}",
    response_model=OperationTraceResponse,
    tags=["Integração"],
    dependencies=[Depends(require_roles("operations", "admin"))],
    responses=OPERATION_TRACE_RESPONSES,
    openapi_extra={"parameters": [CORRELATION_REQUEST_PARAMETER]},
)
def operation_trace(correlation_id: UUID, session: Session = Depends(get_session)) -> dict:
    correlation_value = str(correlation_id)
    entries = session.scalars(select(AuditLog).where(AuditLog.correlation_id == correlation_value).order_by(AuditLog.occurred_at)).all()
    events = session.scalars(select(OutboxEvent).where(OutboxEvent.correlation_id == correlation_value).order_by(OutboxEvent.occurred_at)).all()
    return {"correlationId": correlation_value, "audit": [{"occurredAt": a.occurred_at, "module": a.module, "operation": a.operation, "result": a.result, "entityId": a.entity_id, "details": a.details} for a in entries], "events": [{"eventId": e.event_id, "eventType": e.event_type, "status": e.status, "attempts": e.attempts} for e in events]}


@app.get("/api/v1/demo/state", tags=["Demonstração"], dependencies=[Depends(require_roles("admin"))])
def demo_state(session: Session = Depends(get_session)) -> dict:
    return {"customers": session.query(Customer).count(), "contracts": session.query(Contract).count(), "invoices": session.query(Invoice).count(), "tickets": session.query(Ticket).count(), "processes": session.query(ProcessInstance).count(), "legacyMappings": session.query(LegacyIdMapping).count()}
