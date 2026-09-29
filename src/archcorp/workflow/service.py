from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from archcorp.integration.service import audit
from archcorp.workflow.models import ProcessInstance, ProcessTask


def _start(session: Session, envelope: dict, process_type: str, reference_field: str, due_hours: int) -> None:
    payload = envelope["payload"]
    reference_id = payload[reference_field]
    if session.scalar(select(ProcessInstance).where(ProcessInstance.process_type == process_type, ProcessInstance.reference_id == reference_id)):
        return
    process = ProcessInstance(process_type=process_type, reference_id=reference_id, customer_id=payload["customerId"], due_at=datetime.now(timezone.utc) + timedelta(hours=due_hours))
    session.add(process)
    session.flush()
    session.add(ProcessTask(process_id=process.process_id, title="Executar " + process_type.lower().replace("_", " "), due_at=process.due_at))
    audit(session, envelope["correlationId"], "workflow", f"start_{process_type.lower()}", "success", process.process_id, referenceId=reference_id)


def handle_contract_activated(session: Session, envelope: dict) -> None:
    _start(session, envelope, "ONBOARDING", "contractId", 72)


def handle_ticket_opened(session: Session, envelope: dict) -> None:
    _start(session, envelope, "TICKET_RESOLUTION", "ticketId", envelope["payload"].get("slaHours") or 24)


def handle_ticket_entitlement_reconciled(session: Session, envelope: dict) -> None:
    payload = envelope["payload"]
    process = session.scalar(select(ProcessInstance).where(
        ProcessInstance.process_type == "TICKET_RESOLUTION",
        ProcessInstance.reference_id == payload["ticketId"],
    ))
    if not process:
        return
    if payload["status"] == "OPEN":
        process.due_at = datetime.fromisoformat(payload["dueAt"].replace("Z", "+00:00"))
    else:
        process.state = "CANCELLED"
        process.due_at = None
    for task in session.scalars(select(ProcessTask).where(ProcessTask.process_id == process.process_id)):
        task.due_at = process.due_at
        if process.state == "CANCELLED":
            task.state = "CANCELLED"
    audit(session, envelope["correlationId"], "workflow", "reconcile_ticket_deadline", "success", process.process_id)


def handle_ticket_resolved(session: Session, envelope: dict) -> None:
    process = session.scalar(select(ProcessInstance).where(
        ProcessInstance.process_type == "TICKET_RESOLUTION",
        ProcessInstance.reference_id == envelope["payload"]["ticketId"],
    ))
    if not process:
        return
    process.state = "COMPLETED"
    for task in session.scalars(select(ProcessTask).where(ProcessTask.process_id == process.process_id)):
        task.state = "DONE"
    audit(session, envelope["correlationId"], "workflow", "complete_ticket_resolution", "success", process.process_id)


def count_processes(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(ProcessInstance)) or 0


def handle_contract_closed(session: Session, envelope: dict) -> None:
    """Encerra a preparação de retirada do contrato; o processo não fica pendente após o fim da locação."""
    process = session.scalar(select(ProcessInstance).where(
        ProcessInstance.process_type == "ONBOARDING",
        ProcessInstance.reference_id == envelope["payload"]["contractId"],
    ))
    if not process or process.state in {"COMPLETED", "CANCELLED"}:
        return
    process.state = "COMPLETED"
    for task in session.scalars(select(ProcessTask).where(ProcessTask.process_id == process.process_id)):
        if task.state not in {"DONE", "CANCELLED"}:
            task.state = "CANCELLED"
    audit(session, envelope["correlationId"], "workflow", "complete_onboarding_on_close", "success", process.process_id)
