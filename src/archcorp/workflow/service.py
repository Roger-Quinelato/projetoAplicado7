from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.infrastructure.db import count_rows
from archcorp.integration.public import audit
from archcorp.workflow.models import ProcessInstance, ProcessTask


def _find_process(session: Session, process_type: str, reference_id: str) -> ProcessInstance | None:
    """Busca o processo de um tipo vinculado à referência."""
    return session.scalar(select(ProcessInstance).where(ProcessInstance.process_type == process_type, ProcessInstance.reference_id == reference_id))


def _tasks(session: Session, process: ProcessInstance) -> list[ProcessTask]:
    """Lista as tarefas do processo."""
    return list(session.scalars(select(ProcessTask).where(ProcessTask.process_id == process.process_id)))


def _parse_utc(value: str) -> datetime:
    """Converte um instante ISO 8601 do evento em datetime UTC."""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _start(session: Session, envelope: dict, process_type: str, reference_field: str, due_at: datetime) -> None:
    """Inicia o processo e sua primeira tarefa uma única vez por referência."""
    payload = envelope["payload"]
    reference_id = payload[reference_field]
    if _find_process(session, process_type, reference_id):
        return
    process = ProcessInstance(process_type=process_type, reference_id=reference_id, customer_id=payload["customerId"], due_at=due_at)
    session.add(process)
    session.flush()
    session.add(ProcessTask(process_id=process.process_id, title="Executar " + process_type.lower().replace("_", " "), due_at=process.due_at))
    audit(session, envelope["correlationId"], "workflow", f"start_{process_type.lower()}", "success", process.process_id, referenceId=reference_id)


def handle_contract_activated(session: Session, envelope: dict) -> None:
    """Consumidor de ContractActivated.v1: inicia a preparação de retirada (72 h)."""
    _start(session, envelope, "ONBOARDING", "contractId", datetime.now(timezone.utc) + timedelta(hours=72))


def handle_ticket_opened(session: Session, envelope: dict) -> None:
    """Consumidor de TicketOpened.v1: inicia a resolução com o prazo publicado por Support.

    O prazo é o `dueAt` do chamado, nunca o instante do despacho: atraso ou
    reentrega da outbox não estende o SLA. Chamado pendente de elegibilidade
    (sem `dueAt`) recebe prazo operacional provisório de 24 h contado da
    abertura, substituído na reconciliação.
    """
    payload = envelope["payload"]
    if payload.get("dueAt"):
        due_at = _parse_utc(payload["dueAt"])
    else:
        opened_at = _parse_utc(payload.get("openedAt") or envelope["occurredAt"])
        due_at = opened_at + timedelta(hours=payload.get("slaHours") or 24)
    _start(session, envelope, "TICKET_RESOLUTION", "ticketId", due_at)


def handle_ticket_entitlement_reconciled(session: Session, envelope: dict) -> None:
    """Consumidor de TicketEntitlementReconciled.v1: ajusta o prazo ou cancela a resolução."""
    payload = envelope["payload"]
    process = _find_process(session, "TICKET_RESOLUTION", payload["ticketId"])
    if not process:
        return
    if payload["status"] == "OPEN":
        process.due_at = _parse_utc(payload["dueAt"])
    else:
        process.state = "CANCELLED"
        process.due_at = None
    for task in _tasks(session, process):
        task.due_at = process.due_at
        if process.state == "CANCELLED":
            task.state = "CANCELLED"
    audit(session, envelope["correlationId"], "workflow", "reconcile_ticket_deadline", "success", process.process_id)


def handle_ticket_resolved(session: Session, envelope: dict) -> None:
    """Consumidor de TicketResolved.v1: conclui o processo e suas tarefas."""
    process = _find_process(session, "TICKET_RESOLUTION", envelope["payload"]["ticketId"])
    if not process:
        return
    process.state = "COMPLETED"
    for task in _tasks(session, process):
        task.state = "DONE"
    audit(session, envelope["correlationId"], "workflow", "complete_ticket_resolution", "success", process.process_id)


def count_processes(session: Session) -> int:
    """Conta os processos gravados."""
    return count_rows(session, ProcessInstance)


def handle_contract_closed(session: Session, envelope: dict) -> None:
    """Encerra a preparação de retirada do contrato; o processo não fica pendente após o fim da locação."""
    process = _find_process(session, "ONBOARDING", envelope["payload"]["contractId"])
    if not process or process.state in {"COMPLETED", "CANCELLED"}:
        return
    process.state = "COMPLETED"
    for task in _tasks(session, process):
        if task.state not in {"DONE", "CANCELLED"}:
            task.state = "CANCELLED"
    audit(session, envelope["correlationId"], "workflow", "complete_onboarding_on_close", "success", process.process_id)
