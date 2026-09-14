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


class CustomerReader(Protocol):
    def get(self, session: Session, customer_id: str) -> CustomerData | None: ...
