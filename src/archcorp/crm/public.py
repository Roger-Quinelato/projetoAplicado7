from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class CustomerData:
    customer_id: str
    name: str
    email: str
    eligible: bool
    consent_service: bool
    active: bool = True

    @property
    def can_contract(self) -> bool:
        """Indica se o cliente está ativo, elegível e com consentimento para originar reserva ou contrato."""
        return self.active and self.eligible and self.consent_service


class CustomerReader(Protocol):
    def get(self, session: Session, customer_id: str) -> CustomerData | None:
        """Lê os dados públicos do cliente ou devolve None."""
