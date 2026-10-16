"""Regras do chamado (T15), sem dependência de HTTP, banco ou framework.

Estados, transições, prioridade, prazo de SLA e estado de SLA ficam aqui para que
rotas e serviço apliquem uma única máquina de estados. O relógio é sempre recebido
como parâmetro: nenhuma função lê a hora do sistema.
"""
import re
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from archcorp.exceptions import InvalidStateError


class TicketStatus(StrEnum):
    PENDING_ENTITLEMENT = "PENDING_ENTITLEMENT"
    OPEN = "OPEN"
    REJECTED_ENTITLEMENT = "REJECTED_ENTITLEMENT"
    RESOLVED = "RESOLVED"


class Priority(StrEnum):
    NORMAL = "NORMAL"
    HIGH = "HIGH"


class SlaStatus(StrEnum):
    PENDING = "PENDING"                # elegibilidade ainda não confirmada: sem SLA
    WITHIN = "WITHIN"                  # chamado aberto, dentro do prazo
    BREACHED = "BREACHED"              # prazo vencido (aberto) ou resolvido depois do prazo
    MET = "MET"                        # resolvido até o prazo
    NOT_APPLICABLE = "NOT_APPLICABLE"  # elegibilidade rejeitada: não há SLA a cumprir


class HistoryAction(StrEnum):
    OPENED = "OPENED"
    ASSIGNED = "ASSIGNED"
    REASSIGNED = "REASSIGNED"
    ENTITLEMENT_CONFIRMED = "ENTITLEMENT_CONFIRMED"
    ENTITLEMENT_REJECTED = "ENTITLEMENT_REJECTED"
    RESOLVED = "RESOLVED"


# Máquina de estados única do chamado. RESOLVED e REJECTED_ENTITLEMENT são finais:
# o plano não prevê reabertura nem pausa de SLA.
TICKET_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.PENDING_ENTITLEMENT: {TicketStatus.OPEN, TicketStatus.REJECTED_ENTITLEMENT},
    TicketStatus.OPEN: {TicketStatus.RESOLVED},
    TicketStatus.REJECTED_ENTITLEMENT: set(),
    TicketStatus.RESOLVED: set(),
}
TRANSITION_MESSAGES = {
    TicketStatus.OPEN: "Somente chamado pendente pode ser reconciliado",
    TicketStatus.REJECTED_ENTITLEMENT: "Somente chamado pendente pode ser reconciliado",
    TicketStatus.RESOLVED: "Somente chamado aberto pode ser resolvido",
}
ASSIGNABLE = {TicketStatus.OPEN, TicketStatus.PENDING_ENTITLEMENT}
HIGH_PRIORITY_CATEGORIES = {"OUTAGE", "SECURITY"}


def ensure_ticket_transition(current: str, target: TicketStatus) -> None:
    if target not in TICKET_TRANSITIONS[TicketStatus(current)]:
        raise InvalidStateError(TRANSITION_MESSAGES.get(target, f"Chamado {current} não pode ir para {target}"))


def ensure_assignable(current: str) -> None:
    if TicketStatus(current) not in ASSIGNABLE:
        raise InvalidStateError("Chamado resolvido ou rejeitado não pode ser atribuído")


def priority_for(category: str) -> Priority:
    """Indisponibilidade e segurança recebem prioridade alta (regra do protótipo desde F3)."""
    return Priority.HIGH if category in HIGH_PRIORITY_CATEGORIES else Priority.NORMAL


def as_utc(value: datetime | None) -> datetime | None:
    """O SQLite devolve datas sem fuso; todas as datas do chamado são gravadas em UTC."""
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def iso_utc(value: datetime | None) -> str | None:
    value = as_utc(value)
    return value.isoformat().replace("+00:00", "Z") if value else None


def due_at(opened_at: datetime, sla_hours: int) -> datetime:
    """O prazo conta da abertura do chamado com o SLA contratado em Contracts.

    Na reconciliação o prazo também conta da abertura: o tempo em que Contracts
    ficou indisponível não estende o SLA do cliente.
    """
    return as_utc(opened_at) + timedelta(hours=sla_hours)


def sla_status(status: str, due: datetime | None, now: datetime, resolved_at: datetime | None = None) -> SlaStatus | None:
    """Estado de SLA determinístico para o instante `now` (fornecido pelo relógio do serviço).

    Devolve None apenas para chamado resolvido antes da T15, sem `resolvedAt` gravado.
    """
    current = TicketStatus(status)
    if current == TicketStatus.PENDING_ENTITLEMENT:
        return SlaStatus.PENDING
    if current == TicketStatus.REJECTED_ENTITLEMENT:
        return SlaStatus.NOT_APPLICABLE
    due = as_utc(due)
    if due is None:
        return SlaStatus.PENDING
    if current == TicketStatus.RESOLVED:
        resolved_at = as_utc(resolved_at)
        if resolved_at is None:
            return None
        return SlaStatus.MET if resolved_at <= due else SlaStatus.BREACHED
    return SlaStatus.WITHIN if as_utc(now) <= due else SlaStatus.BREACHED


# Conteúdo que não pode entrar na descrição do chamado (AGENTS.md e RNF-03): documento,
# cartão ou telefone (11 ou mais dígitos, com separadores simples), placa e e-mail.
_SENSITIVE_PATTERNS = (
    re.compile(r"\d(?:[ .\-/]?\d){10,}"),
    re.compile(r"\b[A-Z]{3}-?\d[A-Z0-9]\d{2}\b", re.IGNORECASE),
    re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
)
SENSITIVE_DESCRIPTION_MESSAGE = (
    "A descrição não pode conter documento, cartão, telefone, placa ou e-mail; registre apenas o relato da ocorrência"
)


def contains_sensitive_data(text: str) -> bool:
    return any(pattern.search(text) for pattern in _SENSITIVE_PATTERNS)
