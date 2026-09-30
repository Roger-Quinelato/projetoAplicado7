from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from archcorp.contracts.routes import configure as configure_contracts, router as contracts_router, set_replay
from archcorp.contracts.service import ContractService
from archcorp.crm.service import CustomerService
from archcorp.crm.routes import router as crm_router
from archcorp.errors import (
    install_problem_openapi,
    problem_content,
    problem_example,
    problem_response,
    register_error_handlers,
)
from archcorp.finance.service import count_invoices, handle_contract_activated as finance_contract_activated
from archcorp.finance.routes import router as finance_router
from archcorp.infrastructure.db import engine, get_session, protect_public_demo_tables
from archcorp.infrastructure.migrate import upgrade_to_head
from archcorp.integration.models import AuditLog, OutboxEvent
from archcorp.integration.service import EventDispatcher, LegacyIdService, audit
from archcorp.observability import correlation_id_var, logger, metrics_middleware, render_metrics
from archcorp.schemas import (
    EXAMPLE_CONTRACT_ACTIVATED_RESPONSE,
    EXAMPLE_CONTRACT_DRAFT_RESPONSE,
    EXAMPLE_CONTRACT_EVENT_ID,
    EXAMPLE_CONTRACT_ID,
    EXAMPLE_CORRELATION_ID,
    EXAMPLE_PENDING_TICKET_RESPONSE,
    EXAMPLE_TICKET_ID,
    EXAMPLE_TICKET_RESPONSE,
    IDEMPOTENCY_KEY_MAX_LENGTH,
    ContractActivationResponse,
    ContractDraftCreate,
    ContractDraftResponse,
    DemoStateResponse,
    DispatchResponse,
    HealthResponse,
    LegacyIdResponse,
    EntitlementResponse,
    FailureResponse,
    OperationTraceResponse,
    ReprocessResponse,
    TicketCreate,
    TicketResponse,
)
from archcorp.security import require_roles
from archcorp.config import settings
from archcorp.support.service import TicketService
from archcorp.support.routes import router as support_router
from archcorp.workflow.routes import router as workflow_router
from archcorp.workflow.service import count_processes, handle_contract_activated as workflow_contract_activated, handle_contract_closed as workflow_contract_closed, handle_ticket_opened, handle_ticket_entitlement_reconciled, handle_ticket_resolved


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

def validation_problem_response(description: str, instance: str, field: str, rule_summary: str, rule_detail: str) -> dict:
    """Documenta um 422 com exemplos de regra de negócio e de validação do corpo."""
    invalid = [{"type": "uuid_parsing", "loc": ["body", field], "msg": "Input should be a valid UUID", "input": "not-a-uuid"}]
    return {
        "description": description,
        "content": problem_content(examples={
            "businessRule": {"summary": rule_summary, "value": problem_example(422, rule_detail, instance, "BUSINESS_RULE_VIOLATION")},
            "validation": {"summary": "Corpo da requisição inválido", "value": {**problem_example(422, invalid, instance), "errors": invalid}},
        }),
    }


COMMON_API_ERRORS = {
    400: {
        "description": "Cabeçalho de correlação inválido.",
        "content": problem_content(problem_example(400, "X-Correlation-ID deve ser UUID", "/api/v1/contracts/drafts")),
    },
    401: {
        "description": "Token ausente ou inválido.",
        "content": problem_content(problem_example(401, "Token ausente ou inválido", "/api/v1/contracts/drafts")),
    },
    403: {
        "description": "Papel sem permissão para a operação.",
        "content": problem_content(problem_example(403, "Papel sem permissão para esta operação", "/api/v1/contracts/drafts")),
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
    409: {
        "description": "Idempotency-Key reutilizada com outro conteúdo ou contrato já existente.",
        "content": problem_content(problem_example(409, "Idempotency-Key já utilizada com outro contrato", "/api/v1/contracts/drafts", "IDEMPOTENCY_CONFLICT")),
    },
    422: validation_problem_response(
        "Entrada inválida ou cliente inexistente, inelegível ou sem consentimento.",
        "/api/v1/contracts/drafts", "customerId",
        "Cliente não pode originar contrato", "Cliente inexistente ou inelegível",
    ),
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
        "content": problem_content(problem_example(404, "Contrato não encontrado", f"/api/v1/contracts/{EXAMPLE_CONTRACT_ID}/activate")),
    },
    409: {
        "description": "Contrato já encerrado ou estado incompatível para ativação.",
        "content": problem_content(problem_example(409, "Somente contrato em rascunho pode ser ativado", f"/api/v1/contracts/{EXAMPLE_CONTRACT_ID}/activate", "INVALID_STATE")),
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
    409: {
        "description": "Idempotency-Key reutilizada com outro chamado.",
        "content": problem_content(problem_example(409, "Idempotency-Key já utilizada com outro chamado", "/api/v1/support/tickets", "IDEMPOTENCY_CONFLICT")),
    },
    422: validation_problem_response(
        "Entrada inválida ou contrato, serviço ou cliente sem elegibilidade.",
        "/api/v1/support/tickets", "contractId",
        "Contrato sem elegibilidade", "Contrato, serviço ou cliente sem elegibilidade",
    ),
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
        "content": problem_content(problem_example(404, "Chamado não encontrado", f"/api/v1/support/tickets/{EXAMPLE_TICKET_ID}/reconcile")),
    },
    409: {
        "description": "Chamado não está pendente de elegibilidade.",
        "content": problem_content(problem_example(409, "Somente chamado pendente pode ser reconciliado", f"/api/v1/support/tickets/{EXAMPLE_TICKET_ID}/reconcile", "INVALID_STATE")),
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
        "content": problem_content(problem_example(404, "Falha não encontrada", f"/api/v1/integration/failures/{EXAMPLE_CONTRACT_EVENT_ID}/reprocess")),
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
configure_contracts(contracts)
dispatcher = EventDispatcher({
    "ContractActivated.v1": [("finance", finance_contract_activated), ("workflow-preparacao-retirada", workflow_contract_activated)],
    "ContractClosed.v1": [("workflow-encerramento-contrato", workflow_contract_closed)],
    "TicketOpened.v1": [("workflow-ticket-resolution", handle_ticket_opened)],
    "TicketEntitlementReconciled.v1": [("workflow-ticket-entitlement", handle_ticket_entitlement_reconciled)],
    "TicketResolved.v1": [("workflow-ticket-resolution-complete", handle_ticket_resolved)],
    "CustomerUpdated.v1": [("contracts-customer-projection", ContractService.apply_customer_update)],
})


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Valida o segredo da demo pública, aplica as migrações e protege as tabelas antes de atender."""
    if settings.public_demo and (not settings.demo_access_token or len(settings.demo_access_token) < 24 or settings.demo_access_token.startswith("demo-")):
        raise RuntimeError("PUBLIC_DEMO exige DEMO_ACCESS_TOKEN aleatório com pelo menos 24 caracteres")
    with engine.begin() as connection:
        upgrade_to_head(connection)
        protect_public_demo_tables(connection)
    yield


app = FastAPI(title="Localiza Integração Cenário 4", version="1.0.0", description="API demonstrativa para CRM, reservas e contratos, financeiro e faturamento, atendimento e assistência 24h, workflow e integração.", lifespan=lifespan)
app.middleware("http")(metrics_middleware)
register_error_handlers(app)
install_problem_openapi(app)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    """Propaga X-Correlation-ID na requisição, nos logs e na resposta; 400 se não for UUID."""
    supplied = request.headers.get("X-Correlation-ID")
    try:
        correlation_id = str(UUID(supplied)) if supplied else str(uuid4())
    except ValueError:
        correlation_id = str(uuid4())
        token = correlation_id_var.set(correlation_id)
        try:
            return problem_response(request, 400, "X-Correlation-ID deve ser UUID", headers={"X-Correlation-ID": correlation_id})
        finally:
            correlation_id_var.reset(token)
    token = correlation_id_var.set(correlation_id)
    try:
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Erro não tratado", extra={"operation": request.url.path, "result": "failure"})
            response = problem_response(request, 500, "Erro interno inesperado")
        response.headers["X-Correlation-ID"] = correlation_id
        logger.info("Requisição concluída", extra={"operation": request.url.path, "result": response.status_code})
        return response
    finally:
        correlation_id_var.reset(token)


@app.get("/health/live", response_model=HealthResponse, response_model_exclude_none=True, tags=["Operação"])
def live() -> dict:
    """Informa que o processo está no ar."""
    return {"status": "UP"}


@app.get(
    "/health/ready",
    response_model=HealthResponse,
    tags=["Operação"],
    responses={503: {"description": "Banco indisponível."}},
)
def ready(session: Session = Depends(get_session)) -> dict:
    """Informa se o banco responde; 503 quando indisponível."""
    try:
        session.execute(text("SELECT 1"))
        return {"status": "UP", "database": "UP"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Banco indisponível") from exc


@app.get(
    "/metrics",
    response_class=PlainTextResponse,
    tags=["Operação"],
    responses={200: {"description": "Contadores e latência no formato de texto do Prometheus.",
                     "content": {"text/plain": {"example": "archcorp_requests_total{operation=\"GET_/health/live\",status=\"200\"} 1\n"}}}},
)
def metrics() -> str:
    """Expõe contadores e latência no formato de texto do Prometheus."""
    return render_metrics()


@app.post(
    "/api/v1/contracts/drafts",
    status_code=201,
    response_model=ContractDraftResponse,
    tags=["Reservas e contratos"],
    dependencies=[Depends(require_roles("commercial", "contracts", "admin"))],
    responses=CONTRACT_DRAFT_RESPONSES,
)
def create_contract_draft(
    body: ContractDraftCreate,
    response: Response,
    idempotency_key: str = Header(
        alias="Idempotency-Key", max_length=IDEMPOTENCY_KEY_MAX_LENGTH, examples=["demo-contract-001"]
    ),
    session: Session = Depends(get_session),
) -> dict:
    """Cria rascunho de contrato para cliente elegível; repetir a Idempotency-Key devolve a mesma resposta."""
    draft_data = body.model_dump()
    draft_data["customerId"] = str(draft_data["customerId"])
    result, replay = contracts.create_draft(session, draft_data, idempotency_key, correlation_id_var.get())
    set_replay(response, replay)
    return result


@app.post(
    "/api/v1/contracts/{contract_id}/activate",
    response_model=ContractActivationResponse,
    tags=["Reservas e contratos"],
    dependencies=[Depends(require_roles("contracts", "admin"))],
    responses=CONTRACT_ACTIVATION_RESPONSES,
)
def activate_contract(
    contract_id: UUID,
    response: Response,
    idempotency_key: str = Header(
        alias="Idempotency-Key", max_length=IDEMPOTENCY_KEY_MAX_LENGTH, examples=["demo-activate-001"]
    ),
    session: Session = Depends(get_session),
) -> dict:
    """Ativa o contrato e grava ContractActivated.v1, que gera cobrança e preparação de retirada."""
    result, replay = contracts.activate(session, str(contract_id), idempotency_key, correlation_id_var.get())
    set_replay(response, replay)
    return result


@app.get(
    "/api/v1/contracts/{contract_id}/entitlement",
    response_model=EntitlementResponse,
    tags=["Reservas e contratos"],
    dependencies=[Depends(require_roles("support", "admin"))],
    responses=ENTITLEMENT_RESPONSES,
)
def entitlement(contract_id: UUID, customerId: UUID, serviceCode: str, session: Session = Depends(get_session)) -> dict:
    """Consulta se o contrato ativo cobre cliente e serviço e qual o SLA."""
    return contracts.entitlement(session, str(contract_id), str(customerId), serviceCode)


@app.post(
    "/api/v1/support/tickets",
    status_code=201,
    response_model=TicketResponse,
    tags=["Atendimento e assistência 24h"],
    dependencies=[Depends(require_roles("support", "admin"))],
    responses=TICKET_RESPONSES,
)
def open_ticket(
    body: TicketCreate,
    response: Response,
    idempotency_key: str = Header(
        alias="Idempotency-Key", max_length=IDEMPOTENCY_KEY_MAX_LENGTH, examples=["demo-ticket-001"]
    ),
    session: Session = Depends(get_session),
) -> dict:
    """Abre chamado com SLA do contrato; sem Contracts disponível, fica pendente de elegibilidade."""
    ticket_data = body.model_dump(mode="json")
    result, replay = tickets.open(session, ticket_data, idempotency_key, correlation_id_var.get())
    set_replay(response, replay)
    return result


@app.post(
    "/api/v1/support/tickets/{ticket_id}/reconcile",
    response_model=TicketResponse,
    tags=["Atendimento e assistência 24h"],
    dependencies=[Depends(require_roles("support", "operations", "admin"))],
    responses=RECONCILIATION_RESPONSES,
)
def reconcile_ticket(ticket_id: UUID, session: Session = Depends(get_session)) -> dict:
    """Revalida a elegibilidade de um chamado pendente e publica o resultado."""
    return tickets.reconcile(session, str(ticket_id), correlation_id_var.get())


@app.post(
    "/api/v1/integration/outbox/dispatch",
    response_model=DispatchResponse,
    tags=["Integração"],
    dependencies=[Depends(require_roles("operations", "admin"))],
    responses=DISPATCH_RESPONSES,
)
def dispatch_outbox(session: Session = Depends(get_session)) -> dict:
    """Despacha os eventos pendentes da outbox aos consumidores internos."""
    return dispatcher.dispatch_pending(session)


@app.get(
    "/api/v1/integration/failures",
    response_model=list[FailureResponse],
    tags=["Integração"],
    dependencies=[Depends(require_roles("operations", "admin"))],
    responses=FAILURE_LIST_RESPONSES,
)
def list_failures(session: Session = Depends(get_session)) -> list[dict]:
    """Lista eventos que atingiram o limite de tentativas."""
    failures = session.scalars(select(OutboxEvent).where(OutboxEvent.status == "FAILED")).all()
    return [{"eventId": e.event_id, "eventType": e.event_type, "attempts": e.attempts, "reason": e.last_error, "correlationId": e.correlation_id} for e in failures]


@app.post(
    "/api/v1/integration/failures/{event_id}/reprocess",
    response_model=ReprocessResponse,
    tags=["Integração"],
    dependencies=[Depends(require_roles("operations", "admin"))],
    responses=REPROCESS_RESPONSES,
)
def reprocess(event_id: UUID, session: Session = Depends(get_session)) -> dict:
    """Recoloca um evento com falha em PENDING para novo despacho, com auditoria."""
    event = session.get(OutboxEvent, str(event_id))
    if not event or event.status != "FAILED":
        raise HTTPException(status_code=404, detail="Falha não encontrada")
    event.status = "PENDING"
    event.last_error = None
    audit(session, correlation_id_var.get(), "integration", "reprocess_event", "scheduled", event.event_id, previousAttempts=event.attempts)
    event.attempts = 0
    session.commit()
    return {"eventId": event.event_id, "status": "PENDING"}


@app.get(
    "/api/v1/integration/legacy-ids/{source_system}/{legacy_id}",
    response_model=LegacyIdResponse,
    tags=["Integração"],
    dependencies=[Depends(require_roles("commercial", "operations", "admin"))],
    responses={
        **COMMON_API_ERRORS,
        404: {
            "description": "Identificador legado não mapeado.",
            "content": problem_content(problem_example(404, "Identificador legado não encontrado", "/api/v1/integration/legacy-ids/CRM/WEB-LOCALIZA-9999")),
        },
    },
)
def resolve_legacy_id(source_system: str, legacy_id: str, session: Session = Depends(get_session)) -> dict:
    """Resolve um identificador legado para o UUID global."""
    mapping = LegacyIdService.resolve(session, source_system, legacy_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="Identificador legado não encontrado")
    return LegacyIdService.as_dict(mapping)


@app.get(
    "/api/v1/operations/{correlation_id}",
    response_model=OperationTraceResponse,
    tags=["Integração"],
    dependencies=[Depends(require_roles("operations", "admin"))],
    responses=OPERATION_TRACE_RESPONSES,
)
def operation_trace(correlation_id: UUID, session: Session = Depends(get_session)) -> dict:
    """Mostra a auditoria e os eventos de uma operação pelo correlationId."""
    correlation_value = str(correlation_id)
    entries = session.scalars(select(AuditLog).where(AuditLog.correlation_id == correlation_value).order_by(AuditLog.occurred_at)).all()
    events = session.scalars(select(OutboxEvent).where(OutboxEvent.correlation_id == correlation_value).order_by(OutboxEvent.occurred_at)).all()
    return {"correlationId": correlation_value, "audit": [{"occurredAt": a.occurred_at, "module": a.module, "operation": a.operation, "result": a.result, "entityId": a.entity_id, "details": a.details} for a in entries], "events": [{"eventId": e.event_id, "eventType": e.event_type, "status": e.status, "attempts": e.attempts} for e in events]}


@app.get("/api/v1/demo/state", response_model=DemoStateResponse, tags=["Demonstração"], dependencies=[Depends(require_roles("admin"))])
def demo_state(session: Session = Depends(get_session)) -> dict:
    """Resume a quantidade de registros de cada módulo."""
    return {"customers": CustomerService.count(session), "contracts": ContractService.count(session), "invoices": count_invoices(session),
            "tickets": TicketService.count(session), "processes": count_processes(session), "legacyMappings": LegacyIdService.count(session)}


app.include_router(crm_router)
app.include_router(contracts_router)
app.include_router(finance_router)
app.include_router(support_router)
app.include_router(workflow_router)

web_dist = Path(__file__).resolve().parents[2] / "web" / "dist"
if web_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=web_dist / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def web_home() -> FileResponse:
        """Entrega a interface web compilada."""
        return FileResponse(web_dist / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    def web_fallback(path: str) -> FileResponse:
        """Entrega a interface para rotas do frontend; rotas de API inexistentes devolvem 404."""
        if path.startswith(("api/", "health/", "assets/")):
            raise HTTPException(404, "Rota não encontrada")
        return FileResponse(web_dist / "index.html")
