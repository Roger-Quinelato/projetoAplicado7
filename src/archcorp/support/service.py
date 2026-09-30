from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from archcorp.config import settings
from archcorp.contracts.public import ContractEntitlementPort
from archcorp.exceptions import BusinessRuleError, InvalidStateError
from archcorp.infrastructure.db import count_rows, get_or_raise
from archcorp.integration.service import IdempotencyStore, audit, enqueue
from archcorp.support.models import Ticket


class TicketService:
    def __init__(self, contracts: ContractEntitlementPort):
        """Recebe a porta de elegibilidade de contratos."""
        self.contracts = contracts

    def open(self, session: Session, data: dict, idempotency_key: str, correlation_id: str) -> tuple[dict, bool]:
        """Abre chamado com prioridade e SLA; sem Contracts, fica pendente. Idempotente pela Idempotency-Key."""
        request = {field: data[field] for field in ("customerId", "contractId", "serviceCode", "category")}
        stored = IdempotencyStore.replay(session, idempotency_key, "open_ticket", request, "Idempotency-Key já utilizada com outro chamado")
        if stored:
            return stored, True
        if settings.contract_adapter_available:
            entitlement = self.contracts.entitlement(session, data["contractId"], data["customerId"], data["serviceCode"])
            if not entitlement["eligible"]:
                raise BusinessRuleError("Contrato, serviço ou cliente sem elegibilidade")
            status, sla_hours = "OPEN", entitlement["slaHours"]
        else:
            status, sla_hours = "PENDING_ENTITLEMENT", None
        priority = "HIGH" if data["category"] in {"OUTAGE", "SECURITY"} else "NORMAL"
        due_at = datetime.now(timezone.utc) + timedelta(hours=sla_hours) if sla_hours else None
        ticket = Ticket(
            customer_id=data["customerId"], contract_id=data["contractId"], service_code=data["serviceCode"],
            category=data["category"], description=data["description"], status=status, priority=priority,
            sla_hours=sla_hours, due_at=due_at,
        )
        session.add(ticket)
        session.flush()
        response = self.as_dict(ticket)
        enqueue(session, "TicketOpened.v1", "support", response, correlation_id)
        audit(session, correlation_id, "support", "open_ticket", "success", ticket.ticket_id, status=status)
        IdempotencyStore.save(session, idempotency_key, "open_ticket", request, response)
        session.commit()
        return response, False

    def reconcile(self, session: Session, ticket_id: str, correlation_id: str) -> dict:
        """Revalida a elegibilidade do chamado pendente e publica TicketEntitlementReconciled.v1."""
        ticket = get_or_raise(session, Ticket, ticket_id, "Chamado não encontrado")
        if ticket.status != "PENDING_ENTITLEMENT":
            raise InvalidStateError("Somente chamado pendente pode ser reconciliado")
        entitlement = self.contracts.entitlement(session, ticket.contract_id, ticket.customer_id, ticket.service_code)
        if entitlement["eligible"]:
            ticket.status = "OPEN"
            ticket.sla_hours = entitlement["slaHours"]
            ticket.due_at = datetime.now(timezone.utc) + timedelta(hours=ticket.sla_hours)
            audit(session, correlation_id, "support", "reconcile_entitlement", "success", ticket.ticket_id)
        else:
            ticket.status = "REJECTED_ENTITLEMENT"
            audit(session, correlation_id, "support", "reconcile_entitlement", "rejected", ticket.ticket_id)
        enqueue(session, "TicketEntitlementReconciled.v1", "support", self.as_dict(ticket), correlation_id)
        session.commit()
        return self.as_dict(ticket)

    @staticmethod
    def count(session: Session) -> int:
        """Conta os chamados gravados."""
        return count_rows(session, Ticket)

    @staticmethod
    def as_dict(ticket: Ticket) -> dict:
        """Serializa o chamado no formato da API e dos eventos."""
        return {
            "ticketId": ticket.ticket_id, "customerId": ticket.customer_id, "contractId": ticket.contract_id,
            "serviceCode": ticket.service_code, "category": ticket.category, "status": ticket.status,
            "priority": ticket.priority, "slaHours": ticket.sla_hours,
            "dueAt": ticket.due_at.isoformat().replace("+00:00", "Z") if ticket.due_at else None,
        }
