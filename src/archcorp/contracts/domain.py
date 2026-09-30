"""Estados e transições de reservas e contratos, sem dependência de framework."""
from enum import StrEnum

from archcorp.exceptions import InvalidStateError


class ContractStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class ReservationStatus(StrEnum):
    REQUESTED = "REQUESTED"
    DRAFTED = "DRAFTED"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


CONTRACT_TRANSITIONS: dict[ContractStatus, set[ContractStatus]] = {
    ContractStatus.DRAFT: {ContractStatus.ACTIVE, ContractStatus.CANCELLED},
    ContractStatus.ACTIVE: {ContractStatus.CLOSED},
    ContractStatus.CLOSED: set(),
    ContractStatus.CANCELLED: set(),
}
RESERVATION_TRANSITIONS: dict[ReservationStatus, set[ReservationStatus]] = {
    ReservationStatus.REQUESTED: {ReservationStatus.DRAFTED, ReservationStatus.CANCELLED},
    ReservationStatus.DRAFTED: {ReservationStatus.ACTIVE, ReservationStatus.CANCELLED},
    ReservationStatus.ACTIVE: {ReservationStatus.CLOSED},
    ReservationStatus.CLOSED: set(),
    ReservationStatus.CANCELLED: set(),
}
CONTRACT_MESSAGES = {
    ContractStatus.ACTIVE: "Somente contrato em rascunho pode ser ativado",
    ContractStatus.CLOSED: "Somente contrato ativo pode ser encerrado",
    ContractStatus.CANCELLED: "Somente contrato em rascunho pode ser cancelado",
}


def ensure_contract_transition(current: str, target: ContractStatus) -> None:
    if target not in CONTRACT_TRANSITIONS[ContractStatus(current)]:
        raise InvalidStateError(CONTRACT_MESSAGES.get(target, f"Contrato {current} não pode ir para {target}"))


def ensure_reservation_transition(current: str, target: ReservationStatus) -> None:
    if target not in RESERVATION_TRANSITIONS[ReservationStatus(current)]:
        raise InvalidStateError(f"Reserva {current} não pode ir para {target}")
