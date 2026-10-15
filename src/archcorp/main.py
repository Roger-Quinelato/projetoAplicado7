from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from archcorp.api_docs import COMMON_API_ERRORS
from archcorp.contracts.routes import configure as configure_contracts, router as contracts_router
from archcorp.contracts.service import ContractService
from archcorp.crm.service import CustomerService
from archcorp.crm.routes import router as crm_router
from archcorp.errors import (
    install_problem_openapi,
    problem_response,
    register_error_handlers,
)
from archcorp.finance.service import FinanceService, count_invoices
from archcorp.finance.routes import configure as configure_finance, router as finance_router
from archcorp.infrastructure.db import engine, get_session, protect_public_demo_tables
from archcorp.infrastructure.migrate import upgrade_to_head
from archcorp.integration.service import EventDispatcher
from archcorp.integration.public import LegacyIdService
from archcorp.integration.routes import configure as configure_integration, router as integration_router
from archcorp.observability import correlation_id_var, logger, metrics_middleware, render_metrics
from archcorp.schemas import (
    DemoStateResponse,
    HealthResponse,
)
from archcorp.security import require_roles
from archcorp.config import settings
from archcorp.support.service import TicketService
from archcorp.support.routes import configure as configure_support, router as support_router
from archcorp.workflow.routes import router as workflow_router
from archcorp.workflow.service import count_processes, handle_contract_activated as workflow_contract_activated, handle_contract_closed as workflow_contract_closed, handle_ticket_opened, handle_ticket_entitlement_reconciled, handle_ticket_resolved


customers = CustomerService()
contracts = ContractService(customers)
tickets = TicketService(contracts)
configure_contracts(contracts)
finance = FinanceService()
configure_finance(finance)
configure_support(tickets)
dispatcher = EventDispatcher({
    "ContractActivated.v1": [("finance", finance.handle_contract_activated), ("workflow-preparacao-retirada", workflow_contract_activated)],
    # Todos os consumidores internos e suas inboxes são confirmados na mesma transação.
    "ContractClosed.v1": [("workflow-encerramento-contrato", workflow_contract_closed), ("finance-faturamento-final", finance.handle_contract_closed)],
    "TicketOpened.v1": [("workflow-ticket-resolution", handle_ticket_opened)],
    "TicketEntitlementReconciled.v1": [("workflow-ticket-entitlement", handle_ticket_entitlement_reconciled)],
    "TicketResolved.v1": [("workflow-ticket-resolution-complete", handle_ticket_resolved)],
    "CustomerUpdated.v1": [("contracts-customer-projection", ContractService.apply_customer_update)],
})

configure_integration(dispatcher)

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Valida o segredo da demo pública, aplica as migrações e protege as tabelas antes de atender."""
    if settings.public_demo and (not settings.demo_access_token or len(settings.demo_access_token) < 24 or settings.demo_access_token.startswith("demo-")):
        raise RuntimeError("PUBLIC_DEMO exige DEMO_ACCESS_TOKEN aleatório com pelo menos 24 caracteres")
    if settings.public_demo and settings.finance_allow_future_as_of:
        raise RuntimeError("FINANCE_ALLOW_FUTURE_AS_OF é simulação local e não pode ser usada com PUBLIC_DEMO")
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
    dependencies=[Depends(require_roles("operations", "admin"))],
    responses={**COMMON_API_ERRORS,
               200: {"description": "Contadores e latência no formato de texto do Prometheus, rotulados pelo template da rota.",
                     "content": {"text/plain": {"example": "archcorp_requests_total{operation=\"GET_/health/live\",status=\"200\"} 1\n"}}}},
)
def metrics() -> str:
    """Expõe contadores e latência no formato de texto do Prometheus."""
    return render_metrics()


@app.get("/api/v1/demo/state", response_model=DemoStateResponse, tags=["Demonstração"], dependencies=[Depends(require_roles("admin"))])
def demo_state(session: Session = Depends(get_session)) -> dict:
    """Resume a quantidade de registros de cada módulo."""
    return {"customers": CustomerService.count(session), "contracts": ContractService.count(session), "invoices": count_invoices(session),
            "tickets": TicketService.count(session), "processes": count_processes(session), "legacyMappings": LegacyIdService.count(session)}


app.include_router(integration_router)
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
