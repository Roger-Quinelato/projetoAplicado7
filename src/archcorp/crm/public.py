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
        return self.active and self.eligible and self.consent_service


class CustomerReader(Protocol):
    def get(self, session: Session, customer_id: str) -> CustomerData | None: ...
