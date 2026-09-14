from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from archcorp.config import settings
from archcorp.contracts.public import ContractEntitlementPort
from archcorp.integration.models import IdempotencyRecord
from archcorp.integration.service import audit, enqueue
from archcorp.support.models import Ticket


class TicketService:
    def __init__(self, contracts: ContractEntitlementPort):
        self.contracts = contracts

    def open(self, session: Session, data: dict, idempotency_key: str, correlation_id: str) -> tuple[dict, bool]:
        stored = session.get(IdempotencyRecord, {"key": idempotency_key, "operation": "open_ticket"})
        if stored:
            return stored.response, True
        if settings.contract_adapter_available:
            entitlement = self.contracts.entitlement(session, data["contractId"], data["customerId"], data["serviceCode"])
            if not entitlement["eligible"]:
                raise ValueError("Contrato, serviço ou cliente sem elegibilidade")
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
        session.add(IdempotencyRecord(key=idempotency_key, operation="open_ticket", response=response))
        session.commit()
        return response, False

    def reconcile(self, session: Session, ticket_id: str, correlation_id: str) -> dict:
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            raise LookupError("Chamado não encontrado")
        entitlement = self.contracts.entitlement(session, ticket.contract_id, ticket.customer_id, ticket.service_code)
        if entitlement["eligible"]:
            ticket.status = "OPEN"
            ticket.sla_hours = entitlement["slaHours"]
            ticket.due_at = datetime.now(timezone.utc) + timedelta(hours=ticket.sla_hours)
            audit(session, correlation_id, "support", "reconcile_entitlement", "success", ticket.ticket_id)
        else:
            ticket.status = "REJECTED_ENTITLEMENT"
            audit(session, correlation_id, "support", "reconcile_entitlement", "rejected", ticket.ticket_id)
        session.commit()
        return self.as_dict(ticket)

    @staticmethod
    def as_dict(ticket: Ticket) -> dict:
        return {
            "ticketId": ticket.ticket_id, "customerId": ticket.customer_id, "contractId": ticket.contract_id,
            "serviceCode": ticket.service_code, "category": ticket.category, "status": ticket.status,
            "priority": ticket.priority, "slaHours": ticket.sla_hours,
            "dueAt": ticket.due_at.isoformat().replace("+00:00", "Z") if ticket.due_at else None,
        }
