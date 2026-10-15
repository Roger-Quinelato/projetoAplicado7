"""Casos de uso do chamado (Support): abertura, atribuição, reconciliação e resolução.

As regras de estado, prioridade e SLA ficam em `support.domain`; este serviço
orquestra persistência, histórico, auditoria e outbox na mesma transação.
"""
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from archcorp.config import settings
from archcorp.contracts.public import ContractEntitlementPort, ContractsUnavailableError
from archcorp.exceptions import (
    BusinessRuleError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ServiceUnavailableError,
)
from archcorp.integration.public import IdempotencyStore, audit, enqueue
from archcorp.observability import logger
from archcorp.support import domain
from archcorp.support.domain import HistoryAction, TicketStatus
from archcorp.support.models import Ticket, TicketAssignment, TicketHistory


Clock = Callable[[], datetime]
OPEN_OPERATION = "open_ticket"
OPEN_REQUEST_FIELDS = ("customerId", "contractId", "serviceCode", "category", "description")
# Registros gravados antes da T15 não têm impressão digital; comparam os campos que a resposta guarda.
LEGACY_COMPARED_FIELDS = ("customerId", "contractId", "serviceCode", "category")
# Falhas tratadas como indisponibilidade de Contracts (adaptador, timeout ou conexão).
UNAVAILABLE_ERRORS = (ContractsUnavailableError, TimeoutError, ConnectionError)
UNAVAILABLE_MESSAGE = "Contracts indisponível; o chamado permanece em PENDING_ENTITLEMENT"
PENDING_BATCH_MAX = 200


def system_clock() -> datetime:
    return datetime.now(timezone.utc)


class TicketService:
    def __init__(self, contracts: ContractEntitlementPort, clock: Clock = system_clock):
        self.contracts = contracts
        self.clock = clock

    def now(self) -> datetime:
        return domain.as_utc(self.clock())

    # ---------- Abertura ----------

    def open(self, session: Session, data: dict, idempotency_key: str, correlation_id: str,
             actor_role: str | None = None) -> tuple[dict, bool]:
        request = {field: data[field] for field in OPEN_REQUEST_FIELDS}
        stored = self._replay(session, idempotency_key, request)
        if stored is not None:
            return stored, True
        entitlement = self._entitlement(data["contractId"], data["customerId"], data["serviceCode"], session)
        if entitlement is not None and not entitlement["eligible"]:
            raise BusinessRuleError("Contrato, serviço ou cliente sem elegibilidade")
        opened_at = self.now()
        if entitlement is None:
            status, sla_hours, due = TicketStatus.PENDING_ENTITLEMENT, None, None
        else:
            status, sla_hours = TicketStatus.OPEN, entitlement["slaHours"]
            due = domain.due_at(opened_at, sla_hours)
        ticket = Ticket(
            customer_id=data["customerId"], contract_id=data["contractId"], service_code=data["serviceCode"],
            category=data["category"], description=data["description"], status=status,
            priority=domain.priority_for(data["category"]), sla_hours=sla_hours, due_at=due, opened_at=opened_at,
        )
        session.add(ticket)
        session.flush()
        response = self.as_dict(ticket, opened_at)
        enqueue(session, "TicketOpened.v1", "support", response, correlation_id)
        self._record(session, ticket, HistoryAction.OPENED, None, correlation_id, actor_role, opened_at, response["slaStatus"])
        audit(session, correlation_id, "support", "open_ticket", "success", ticket.ticket_id,
              status=status, priority=ticket.priority, slaStatus=response["slaStatus"], actorRole=actor_role)
        IdempotencyStore.save(session, idempotency_key, OPEN_OPERATION, request, response)
        session.commit()
        return response, False

    @staticmethod
    def _replay(session: Session, key: str, request: dict) -> dict | None:
        return IdempotencyStore.replay(
            session, key, OPEN_OPERATION, request, "Idempotency-Key já utilizada com outro chamado",
            legacy_fields=LEGACY_COMPARED_FIELDS,
        )

    def _entitlement(self, contract_id: str, customer_id: str, service_code: str, session: Session) -> dict | None:
        """Consulta Contracts pela porta pública; devolve None quando Contracts está indisponível."""
        if not settings.contract_adapter_available:
            reason = "adaptador desativado"
        else:
            try:
                return self.contracts.entitlement(session, contract_id, customer_id, service_code)
            except UNAVAILABLE_ERRORS as exc:
                reason = type(exc).__name__
        logger.warning(f"Contracts indisponível na consulta de elegibilidade ({reason})",
                       extra={"operation": "support_entitlement", "result": "unavailable"})
        return None

    # ---------- Responsável ----------

    def assign(self, session: Session, ticket_id: str, owner: str, correlation_id: str,
               actor_role: str | None = None) -> dict:
        ticket = self._require(session, ticket_id, lock=True)
        if ticket.status not in domain.ASSIGNABLE:
            raise ConflictError("Chamado não pode ser atribuído neste estado")
        assignment = session.get(TicketAssignment, ticket.ticket_id)
        previous = assignment.owner if assignment else None
        if previous == owner:
            return self.detail(session, ticket)
        if assignment:
            assignment.owner = owner
        else:
            session.add(TicketAssignment(ticket_id=ticket.ticket_id, owner=owner))
        action = HistoryAction.ASSIGNED if previous is None else HistoryAction.REASSIGNED
        now = self.now()
        sla = self._sla(ticket, now)
        self._record(session, ticket, action, ticket.status, correlation_id, actor_role, now, sla,
                     owner=owner, previous_owner=previous)
        audit(session, correlation_id, "support", "assign_ticket", "success", ticket.ticket_id,
              action=action, owner=owner, previousOwner=previous, actorRole=actor_role)
        session.flush()
        response = self.detail(session, ticket)
        session.commit()
        return response

    # ---------- Resolução ----------

    def resolve(self, session: Session, ticket_id: str, correlation_id: str,
                actor_role: str | None = None, idempotency_key: str | None = None) -> tuple[dict, bool]:
        ticket = self._require(session, ticket_id, lock=True)
        request = {"ticketId": ticket_id, "command": "resolve"}
        if idempotency_key:
            replay = IdempotencyStore.replay(session, idempotency_key, "support_ticket_command", request, "Idempotency-Key já utilizada em outro comando ou chamado")
            if replay is not None:
                return replay, True
        if ticket.status != TicketStatus.OPEN:
            raise ConflictError("Somente chamado aberto pode ser resolvido")
        previous = ticket.status
        domain.ensure_ticket_transition(previous, TicketStatus.RESOLVED)
        now = self.now()
        self._transition(session, ticket, previous, status=TicketStatus.RESOLVED, resolved_at=now)
        payload = self.as_dict(ticket, now)
        owner = self._owner(session, ticket.ticket_id)
        enqueue(session, "TicketResolved.v1", "support", payload, correlation_id)
        self._record(session, ticket, HistoryAction.RESOLVED, previous, correlation_id, actor_role, now,
                     payload["slaStatus"], owner=owner)
        audit(session, correlation_id, "support", "resolve_ticket", "success", ticket.ticket_id,
              slaStatus=payload["slaStatus"], owner=owner, actorRole=actor_role)
        response = self.detail(session, ticket)
        if idempotency_key:
            IdempotencyStore.save(session, idempotency_key, "support_ticket_command", request, response)
        session.commit()
        return response, False

    # ---------- Reconciliação ----------

    def reconcile(self, session: Session, ticket_id: str, correlation_id: str,
                  actor_role: str | None = None, idempotency_key: str | None = None) -> tuple[dict, bool]:
        ticket = self._require(session, ticket_id, lock=True)
        request = {"ticketId": ticket_id, "command": "reconcile"}
        if idempotency_key:
            replay = IdempotencyStore.replay(session, idempotency_key, "support_ticket_command", request, "Idempotency-Key já utilizada em outro comando ou chamado")
            if replay is not None:
                return replay, True
        domain.ensure_ticket_transition(ticket.status, TicketStatus.OPEN)
        entitlement = self._entitlement(ticket.contract_id, ticket.customer_id, ticket.service_code, session)
        if entitlement is None:
            audit(session, correlation_id, "support", "reconcile_entitlement", "unavailable", ticket.ticket_id, actorRole=actor_role)
            session.commit()
            raise ServiceUnavailableError(UNAVAILABLE_MESSAGE)
        result = self._apply_reconciliation(session, ticket, entitlement, correlation_id, actor_role, commit=False)
        if idempotency_key:
            IdempotencyStore.save(session, idempotency_key, "support_ticket_command", request, result)
        session.commit()
        return result, False

    def reconcile_pending(self, session: Session, correlation_id: str, actor_role: str | None = None,
                          limit: int = PENDING_BATCH_MAX) -> dict:
        """Reconcilia em lote os chamados pendentes; cada chamado é confirmado em sua própria transação.

        Repetir a operação é seguro: só chamados ainda em PENDING_ENTITLEMENT são consultados.
        Se Contracts cair no meio do lote, os já reconciliados permanecem e o restante continua pendente.
        """
        pending = session.scalars(select(Ticket).where(Ticket.status == TicketStatus.PENDING_ENTITLEMENT)
                                  .order_by(Ticket.opened_at, Ticket.ticket_id).limit(limit)).all()
        reconciled: list[dict] = []
        available = True
        for ticket in pending:
            entitlement = self._entitlement(ticket.contract_id, ticket.customer_id, ticket.service_code, session)
            if entitlement is None:
                available = False
                break
            try:
                reconciled.append(self._apply_reconciliation(session, ticket, entitlement, correlation_id, actor_role))
            except InvalidStateError:
                # Outra operação reconciliou o chamado entre a leitura e a atualização; nada foi gravado aqui.
                logger.info("Chamado alterado durante a reconciliação em lote; ignorado",
                            extra={"operation": "reconcile_pending", "result": "skipped"})
        remaining = session.scalar(select(func.count()).select_from(Ticket)
                                   .where(Ticket.status == TicketStatus.PENDING_ENTITLEMENT)) or 0
        confirmed = sum(1 for item in reconciled if item["status"] == TicketStatus.OPEN)
        summary = {"confirmed": confirmed, "rejected": len(reconciled) - confirmed, "remaining": remaining,
                   "contractsAvailable": available, "tickets": reconciled}
        audit(session, correlation_id, "support", "reconcile_pending", "success" if available else "interrupted", None,
              confirmed=summary["confirmed"], rejected=summary["rejected"], remaining=remaining, actorRole=actor_role)
        session.commit()
        if not available and not reconciled:
            raise ServiceUnavailableError("Contracts indisponível; nenhum chamado pendente foi reconciliado")
        return summary

    def _apply_reconciliation(self, session: Session, ticket: Ticket, entitlement: dict, correlation_id: str,
                              actor_role: str | None, *, commit: bool = True) -> dict:
        ticket = self._require(session, ticket.ticket_id, lock=True)
        previous = ticket.status
        now = self.now()
        if entitlement["eligible"]:
            target, action, result = TicketStatus.OPEN, HistoryAction.ENTITLEMENT_CONFIRMED, "success"
            sla_hours = entitlement["slaHours"]
            values = {"sla_hours": sla_hours, "due_at": domain.due_at(ticket.opened_at or now, sla_hours)}
        else:
            target, action, result = TicketStatus.REJECTED_ENTITLEMENT, HistoryAction.ENTITLEMENT_REJECTED, "rejected"
            values = {}
        domain.ensure_ticket_transition(previous, target)
        self._transition(session, ticket, previous, status=target, reconciled_at=now, **values)
        payload = self.as_dict(ticket, now)
        enqueue(session, "TicketEntitlementReconciled.v1", "support", payload, correlation_id)
        self._record(session, ticket, action, previous, correlation_id, actor_role, now, payload["slaStatus"],
                     owner=self._owner(session, ticket.ticket_id))
        audit(session, correlation_id, "support", "reconcile_entitlement", result, ticket.ticket_id,
              status=target, slaStatus=payload["slaStatus"], actorRole=actor_role)
        if commit:
            session.commit()
        return payload

    # ---------- Consultas ----------

    def get(self, session: Session, ticket_id: str) -> dict:
        return self.detail(session, self._require(session, ticket_id))

    def list_tickets(self, session: Session, limit: int = 200) -> list[dict]:
        now = self.now()
        tickets = session.scalars(select(Ticket).order_by(Ticket.ticket_id).limit(limit)).all()
        owners = {a.ticket_id: a.owner for a in session.scalars(
            select(TicketAssignment).where(TicketAssignment.ticket_id.in_([t.ticket_id for t in tickets])))}
        return [{**self.as_dict(t, now), "description": t.description, "owner": owners.get(t.ticket_id)} for t in tickets]

    def history(self, session: Session, ticket_id: str) -> list[dict]:
        ticket = self._require(session, ticket_id)
        entries = session.scalars(select(TicketHistory).where(TicketHistory.ticket_id == ticket.ticket_id)
                                  .order_by(TicketHistory.id)).all()
        return [{"occurredAt": domain.iso_utc(e.occurred_at), "action": e.action, "fromStatus": e.from_status,
                 "toStatus": e.to_status, "owner": e.owner, "previousOwner": e.previous_owner,
                 "actorRole": e.actor_role, "slaStatus": e.sla_status, "correlationId": e.correlation_id}
                for e in entries]

    def detail(self, session: Session, ticket: Ticket) -> dict:
        return {**self.as_dict(ticket), "description": ticket.description, "owner": self._owner(session, ticket.ticket_id)}

    def as_dict(self, ticket: Ticket, now: datetime | None = None) -> dict:
        """Representação pública do chamado, usada na API e nos eventos (sem a descrição)."""
        return {
            "ticketId": ticket.ticket_id, "customerId": ticket.customer_id, "contractId": ticket.contract_id,
            "serviceCode": ticket.service_code, "category": ticket.category, "status": str(ticket.status),
            "priority": str(ticket.priority), "slaHours": ticket.sla_hours, "dueAt": domain.iso_utc(ticket.due_at),
            "openedAt": domain.iso_utc(ticket.opened_at), "resolvedAt": domain.iso_utc(ticket.resolved_at),
            "slaStatus": self._sla(ticket, now or self.now()),
        }

    @staticmethod
    def count(session: Session) -> int:
        return session.scalar(select(func.count()).select_from(Ticket)) or 0

    # ---------- Apoio ----------

    @staticmethod
    def _sla(ticket: Ticket, now: datetime) -> str | None:
        status = domain.sla_status(ticket.status, ticket.due_at, now, ticket.resolved_at)
        return str(status) if status else None

    @staticmethod
    def _require(session: Session, ticket_id: str, *, lock: bool = False) -> Ticket:
        query = select(Ticket).where(Ticket.ticket_id == ticket_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        ticket = session.scalar(query)
        if not ticket:
            raise NotFoundError("Chamado não encontrado")
        return ticket

    @staticmethod
    def _owner(session: Session, ticket_id: str) -> str | None:
        assignment = session.get(TicketAssignment, ticket_id)
        return assignment.owner if assignment else None

    @staticmethod
    def _transition(session: Session, ticket: Ticket, expected: str, **values) -> None:
        """Atualização condicionada ao estado lido: duas execuções concorrentes não aplicam o mesmo efeito."""
        result = session.execute(
            update(Ticket).where(Ticket.ticket_id == ticket.ticket_id, Ticket.status == expected).values(**values)
        )
        if result.rowcount != 1:
            session.rollback()
            raise InvalidStateError("Chamado alterado por outra operação; consulte o estado atual")

    @staticmethod
    def _record(session: Session, ticket: Ticket, action: HistoryAction, from_status: str | None, correlation_id: str,
                actor_role: str | None, occurred_at: datetime, sla_status: str | None, *, owner: str | None = None,
                previous_owner: str | None = None) -> None:
        session.add(TicketHistory(
            ticket_id=ticket.ticket_id, occurred_at=occurred_at, action=str(action), from_status=from_status,
            to_status=str(ticket.status), owner=owner, previous_owner=previous_owner, actor_role=actor_role,
            sla_status=sla_status, correlation_id=correlation_id,
        ))
