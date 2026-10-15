from typing import Protocol

from sqlalchemy.orm import Session


class ContractsUnavailableError(Exception):
    """Levantada por um adaptador de Contracts quando a consulta não pode ser respondida.

    O chamador trata a indisponibilidade (Support abre o chamado em `PENDING_ENTITLEMENT`).
    O adaptador interno do protótipo não a levanta; simuladores e conectores futuros sim.
    """


class ContractEntitlementPort(Protocol):
    def entitlement(self, session: Session, contract_id: str, customer_id: str, service_code: str) -> dict:
        """Devolve `{"eligible": bool, "slaHours": int | None}` para contrato ativo, cliente e serviço."""
        ...
