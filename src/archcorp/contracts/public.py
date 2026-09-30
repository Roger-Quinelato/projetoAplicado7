from typing import Protocol

from sqlalchemy.orm import Session


class ContractEntitlementPort(Protocol):
    def entitlement(self, session: Session, contract_id: str, customer_id: str, service_code: str) -> dict:
        """Informa se o contrato ativo cobre cliente e serviço e qual o SLA em horas."""
