from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.errors import problem_content, problem_example
from archcorp.finance.models import Payment
from archcorp.finance.service import FinanceService
from archcorp.infrastructure.db import get_session
from archcorp.observability import correlation_id_var
from archcorp.schemas import EXAMPLE_CONTRACT_ID, EXAMPLE_CUSTOMER_ID, IDEMPOTENCY_KEY_MAX_LENGTH
from archcorp.security import require_roles


router = APIRouter(prefix="/api/v1/finance", tags=["Financeiro e faturamento"])

# Matriz de autorização do Financeiro (docs/TDD_LOCALIZA.md).
FINANCE_READERS = require_roles("finance", "operations", "admin")
FINANCE_OPERATORS = require_roles("finance", "admin")
OVERDUE_OPERATORS = require_roles("finance", "operations", "admin")


class _Services:
    finance: FinanceService | None = None


def configure(finance: FinanceService) -> None:
    """Recebe o serviço montado pela composição da aplicação (o mesmo usado pelos consumidores de eventos)."""
    _Services.finance = finance


def finance_service() -> FinanceService:
    return _Services.finance


EXAMPLE_INVOICE = {
    "invoiceId": "ffffffff-ffff-4fff-8fff-ffffffffffff",
    "contractId": EXAMPLE_CONTRACT_ID,
    "customerId": EXAMPLE_CUSTOMER_ID,
    "kind": "INITIAL",
    "amount": 2500.0,
    "currency": "BRL",
    "dueDate": "2026-10-11",
    "paidAmount": 0.0,
    "balance": 2500.0,
    "status": "OPEN",
    "delinquent": False,
    "overdueSince": None,
    "sourceEventId": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
}
EXAMPLE_PAYMENT = {
    "paymentId": "12121212-1212-4121-8121-121212121212",
    "invoiceId": EXAMPLE_INVOICE["invoiceId"],
    "amount": 2500.0,
    "currency": "BRL",
    "reference": "SIMULATED-001",
}
NOT_FOUND = {404: {"description": "Fatura não encontrada."}}
PAYMENT_PATH = "/api/v1/finance/invoices/ffffffff-ffff-4fff-8fff-ffffffffffff/payments"
REPLAY_HEADERS = {
    "Idempotency-Replayed": {
        "description": "Retorna true quando a API reutiliza a resposta ou o pagamento já registrado.",
        "schema": {"type": "string", "enum": ["true", "false"]},
    },
}


class PaymentInput(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"amount": 2500.00, "currency": "BRL", "reference": "SIMULATED-001"}]})

    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    reference: str = Field(min_length=3, max_length=100)


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_INVOICE]})

    invoiceId: UUID
    contractId: UUID
    customerId: UUID
    kind: Literal["INITIAL", "FINAL"] = Field(description="INITIAL: primeira cobrança (ContractActivated.v1); FINAL: faturamento final (ContractClosed.v1).")
    # Valores monetários como number (float) por compatibilidade com a v1; decimal em string fica para a v2.
    amount: float
    currency: str
    dueDate: date
    paidAmount: float
    balance: float = Field(description="Saldo em aberto: amount - paidAmount, na moeda da fatura.")
    status: Literal["OPEN", "PARTIALLY_PAID", "PAID", "OVERDUE", "CANCELLED"] = Field(
        description="OVERDUE também aparece, calculado na leitura, quando a data UTC passou do vencimento com saldo; "
                    "`delinquent` indica se a inadimplência já foi registrada pela verificação de vencimento.")
    delinquent: bool = Field(description="Inadimplência registrada e ainda com saldo.")
    overdueSince: datetime | None = Field(description="Momento UTC do registro da inadimplência; mantido como histórico após a quitação.")
    sourceEventId: UUID | None = Field(description="eventId que originou a fatura; nulo em faturas anteriores à T12.")


class PaymentResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_PAYMENT]})

    paymentId: UUID
    invoiceId: UUID
    amount: float
    currency: str
    reference: str


class PaymentResultResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{
        "paymentId": EXAMPLE_PAYMENT["paymentId"],
        "invoice": {**EXAMPLE_INVOICE, "paidAmount": 2500.0, "balance": 0.0, "status": "PAID"},
    }]})

    paymentId: UUID
    invoice: InvoiceResponse


class OverdueCheckInput(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"asOf": "2026-10-25"}]})

    asOf: date | None = Field(default=None, description="Data UTC de referência; padrão é a data UTC atual. "
                                                        "Data futura só com FINANCE_ALLOW_FUTURE_AS_OF=true (simulação local).")


class OverdueCheckResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{
        "asOf": "2026-10-25", "evaluatedAt": "2026-10-25T09:00:00Z",
        "markedOverdue": [EXAMPLE_INVOICE["invoiceId"]], "alreadyOverdue": 0,
    }]})

    asOf: date
    evaluatedAt: datetime
    markedOverdue: list[UUID] = Field(description="Faturas que passaram a OVERDUE nesta execução.")
    alreadyOverdue: int = Field(description="Faturas que já estavam com inadimplência registrada.")


class InvoiceCancelInput(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"reason": "Cobrança emitida em duplicidade"}]})

    reason: str = Field(min_length=3, max_length=200,
                        description="Gravado na auditoria; não informe dado pessoal, bancário ou outro conteúdo sensível.")


@router.get("/invoices", response_model=list[InvoiceResponse], dependencies=[Depends(FINANCE_READERS)])
def list_invoices(contractId: UUID | None = None, session: Session = Depends(get_session),
                  service: FinanceService = Depends(finance_service)) -> list[dict]:
    return service.list_invoices(session, str(contractId) if contractId else None)


@router.post(
    "/invoices/overdue-check",
    response_model=OverdueCheckResponse,
    responses={422: {
        "description": "Data de referência futura sem simulação habilitada ou entrada inválida.",
        "content": problem_content(problem_example(
            422, "Data de referência futura exige FINANCE_ALLOW_FUTURE_AS_OF=true (simulação local)",
            "/api/v1/finance/invoices/overdue-check", "BUSINESS_RULE_VIOLATION")),
    }},
    dependencies=[Depends(OVERDUE_OPERATORS)],
)
def check_overdue(body: OverdueCheckInput | None = None, session: Session = Depends(get_session),
                  service: FinanceService = Depends(finance_service)) -> dict:
    """Registra a inadimplência das faturas com saldo e vencimento anterior à data de referência (UTC).

    Comando explícito e idempotente pelo estado: repetir não marca de novo nem duplica auditoria por fatura.
    """
    return service.evaluate_overdue(session, (body or OverdueCheckInput()).asOf, correlation_id_var.get())


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse, responses=NOT_FOUND, dependencies=[Depends(FINANCE_READERS)])
def get_invoice(invoice_id: UUID, session: Session = Depends(get_session), service: FinanceService = Depends(finance_service)) -> dict:
    return service.get(session, str(invoice_id))


@router.post(
    "/invoices/{invoice_id}/payments",
    status_code=201,
    response_model=PaymentResultResponse,
    responses={
        **NOT_FOUND,
        201: {"headers": REPLAY_HEADERS},
        409: {
            "description": "Referência ou Idempotency-Key já usada com outro pagamento, valor acima do saldo, fatura quitada ou cancelada.",
            "content": problem_content(examples={
                "overpayment": {"summary": "Valor acima do saldo", "value": problem_example(409, "Pagamento excede saldo da fatura", PAYMENT_PATH, "CONFLICT")},
                "paid": {"summary": "Fatura quitada", "value": problem_example(409, "Fatura já quitada", PAYMENT_PATH, "CONFLICT")},
                "cancelled": {"summary": "Fatura cancelada", "value": problem_example(409, "Fatura cancelada não recebe pagamento", PAYMENT_PATH, "INVALID_STATE")},
                "idempotency": {"summary": "Chave reutilizada", "value": problem_example(409, "Idempotency-Key já utilizada com outro pagamento", PAYMENT_PATH, "IDEMPOTENCY_CONFLICT")},
            }),
        },
        422: {
            "description": "Entrada inválida ou moeda diferente da fatura.",
            "content": problem_content(problem_example(422, "Moeda diferente da fatura", PAYMENT_PATH, "VALIDATION_ERROR")),
        },
    },
    dependencies=[Depends(FINANCE_OPERATORS)])
def record_payment(
    invoice_id: UUID,
    body: PaymentInput,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=IDEMPOTENCY_KEY_MAX_LENGTH,
                                         description="Opcional; com a chave, repetir o pagamento devolve a resposta original."),
    session: Session = Depends(get_session),
    service: FinanceService = Depends(finance_service),
) -> dict:
    """Registra pagamento simulado (sem PSP): valida moeda, saldo e estado da fatura e atualiza o saldo."""
    result, replay = service.record_payment(session, str(invoice_id), body.model_dump(), idempotency_key, correlation_id_var.get())
    response.headers["Idempotency-Replayed"] = str(replay).lower()
    return result


@router.post(
    "/invoices/{invoice_id}/cancel",
    response_model=InvoiceResponse,
    responses={**NOT_FOUND, 409: {
        "description": "Fatura com pagamento, vencida ou quitada não pode ser cancelada.",
        "content": problem_content(problem_example(409, "Fatura com pagamento registrado não pode ser cancelada",
                                                   "/api/v1/finance/invoices/ffffffff-ffff-4fff-8fff-ffffffffffff/cancel", "INVALID_STATE")),
    }},
    dependencies=[Depends(FINANCE_OPERATORS)],
)
def cancel_invoice(invoice_id: UUID, body: InvoiceCancelInput, session: Session = Depends(get_session),
                   service: FinanceService = Depends(finance_service)) -> dict:
    """Cancela fatura em aberto e sem pagamento; repetir devolve a fatura cancelada."""
    return service.cancel(session, str(invoice_id), body.reason, correlation_id_var.get())


@router.get("/payments", response_model=list[PaymentResponse], dependencies=[Depends(FINANCE_OPERATORS)])
def list_payments(invoiceId: UUID | None = None, session: Session = Depends(get_session)) -> list[dict]:
    """Lista pagamentos, com filtro opcional por fatura."""
    query = select(Payment).order_by(Payment.payment_id).limit(200)
    if invoiceId:
        query = query.where(Payment.invoice_id == str(invoiceId))
    return [{"paymentId": x.payment_id, "invoiceId": x.invoice_id, "amount": float(x.amount),
             "currency": x.currency, "reference": x.reference} for x in session.scalars(query)]
