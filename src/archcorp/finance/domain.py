"""Regras de fatura, pagamento simulado e inadimplência, sem dependência de HTTP ou banco.

Premissas do protótipo acadêmico (a validar com o negócio):
- prazo de pagamento de 10 dias corridos a partir da data UTC do evento que origina a fatura;
- faturamento final por ciclo iniciado: cada ciclo de cobrança (mensal, trimestral ou anual) que
  começa antes da data de encerramento é cobrado integralmente; `ONCE` é cobrado uma única vez;
- a fatura vence quando a data UTC de referência é posterior a `dueDate` e ainda há saldo.
"""
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from archcorp.exceptions import BusinessRuleError, ConflictError, InvalidStateError

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
PAYMENT_TERM_DAYS = 10
CYCLE_MONTHS = {"MONTHLY": 1, "QUARTERLY": 3, "YEARLY": 12}

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(moment: datetime) -> datetime:
    """Exige horário com fuso; um relógio sem fuso tornaria o vencimento dependente da máquina."""
    if moment.tzinfo is None:
        raise ValueError("Horário sem fuso horário; use UTC")
    return moment.astimezone(timezone.utc)


def utc_today(clock: Clock) -> date:
    return as_utc(clock()).date()


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


class InvoiceStatus(StrEnum):
    OPEN = "OPEN"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class InvoiceKind(StrEnum):
    INITIAL = "INITIAL"
    FINAL = "FINAL"


# OVERDUE persistido significa inadimplência registrada pelo comando de vencimento.
INVOICE_TRANSITIONS: dict[InvoiceStatus, set[InvoiceStatus]] = {
    InvoiceStatus.OPEN: {InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.PAID, InvoiceStatus.OVERDUE, InvoiceStatus.CANCELLED},
    InvoiceStatus.PARTIALLY_PAID: {InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.PAID, InvoiceStatus.OVERDUE},
    InvoiceStatus.OVERDUE: {InvoiceStatus.OVERDUE, InvoiceStatus.PAID},
    InvoiceStatus.PAID: set(),
    InvoiceStatus.CANCELLED: set(),
}
TRANSITION_MESSAGES = {
    InvoiceStatus.CANCELLED: "Somente fatura em aberto e sem pagamento pode ser cancelada",
    InvoiceStatus.OVERDUE: "Somente fatura em aberto ou parcialmente paga pode ser marcada como vencida",
}
OPEN_BALANCE = {InvoiceStatus.OPEN, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE}


def ensure_invoice_transition(current: str, target: InvoiceStatus) -> None:
    if target not in INVOICE_TRANSITIONS[InvoiceStatus(current)]:
        raise InvalidStateError(TRANSITION_MESSAGES.get(target, f"Fatura {current} não pode ir para {target}"))


def ensure_payable(current: str) -> None:
    status = InvoiceStatus(current)
    if status == InvoiceStatus.PAID:
        raise InvalidStateError("Fatura já quitada")
    if status == InvoiceStatus.CANCELLED:
        raise InvalidStateError("Fatura cancelada não recebe pagamento")


def status_after_payment(current: str, invoice_amount: Decimal, paid_before: Decimal, payment: Decimal) -> InvoiceStatus:
    """Calcula o estado depois de um pagamento simulado; não altera nada."""
    ensure_payable(current)
    if payment <= ZERO:
        raise BusinessRuleError("Valor do pagamento deve ser positivo")
    balance = money(invoice_amount) - money(paid_before)
    if money(payment) > balance:
        raise ConflictError("Pagamento excede saldo da fatura")
    if balance - money(payment) == ZERO:
        target = InvoiceStatus.PAID
    elif InvoiceStatus(current) == InvoiceStatus.OVERDUE:
        target = InvoiceStatus.OVERDUE
    else:
        target = InvoiceStatus.PARTIALLY_PAID
    ensure_invoice_transition(current, target)
    return target


def is_past_due(current: str, due_date: date, balance: Decimal, today: date) -> bool:
    """Vencida: estado com saldo, saldo positivo e data UTC de referência posterior ao vencimento."""
    return InvoiceStatus(current) in OPEN_BALANCE and balance > ZERO and today > due_date


def effective_status(current: str, due_date: date, balance: Decimal, today: date) -> InvoiceStatus:
    """Estado exibido na leitura: fatura vencida aparece como OVERDUE mesmo antes do registro da inadimplência."""
    status = InvoiceStatus(current)
    if status in {InvoiceStatus.OPEN, InvoiceStatus.PARTIALLY_PAID} and is_past_due(status, due_date, balance, today):
        return InvoiceStatus.OVERDUE
    return status


def due_date_from(occurred_at: datetime) -> date:
    return as_utc(occurred_at).date() + timedelta(days=PAYMENT_TERM_DAYS)


def add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year, month = day.year + month_index // 12, month_index % 12 + 1
    next_month = date(year + (month == 12), month % 12 + 1, 1)
    last_day = (next_month - timedelta(days=1)).day
    return date(year, month, min(day.day, last_day))


def billed_cycles(starts_on: date, ends_on: date, cycle: str) -> int:
    """Quantidade de ciclos iniciados antes da data de encerramento (mínimo 1)."""
    if ends_on < starts_on:
        raise BusinessRuleError("Encerramento anterior ao início do contrato")
    if cycle == "ONCE":
        return 1
    months = CYCLE_MONTHS.get(cycle)
    if months is None:
        raise BusinessRuleError(f"Ciclo de cobrança desconhecido: {cycle}")
    count = 1
    while add_months(starts_on, count * months) < ends_on:
        count += 1
    return count


def final_amount(cycle_amount, starts_on: date, ends_on: date, cycle: str, already_billed: Decimal) -> Decimal:
    """Valor da fatura final: ciclos iniciados menos o já faturado; nunca negativo (crédito não é modelado)."""
    total = money(cycle_amount) * billed_cycles(starts_on, ends_on, cycle)
    return max(money(total - money(already_billed)), ZERO)
