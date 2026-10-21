from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from archcorp.exceptions import NotFoundError
from archcorp.infrastructure.db import count_rows
from archcorp.integration.public import audit
from archcorp.workflow.domain import FINAL_PROCESS_STATES, aggregate_process_state, ensure_process_open, parse_utc, preparation_due, task_change_needed
from archcorp.workflow.models import ProcessInstance, ProcessTask


def _find_process(session: Session, process_type: str, reference_id: str) -> ProcessInstance | None:
    """Busca o processo de um tipo vinculado à referência."""
    return session.scalar(select(ProcessInstance).where(ProcessInstance.process_type == process_type, ProcessInstance.reference_id == reference_id))


def _tasks(session: Session, process: ProcessInstance) -> list[ProcessTask]:
    """Lista as tarefas do processo."""
    return list(session.scalars(select(ProcessTask).where(ProcessTask.process_id == process.process_id)))


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
    """Consumidor de ContractActivated.v1: inicia a preparação de retirada.

    O prazo conta do `occurredAt` da ativação: atraso ou reentrega do despacho não o estende.
    """
    _start(session, envelope, "ONBOARDING", "contractId", preparation_due(parse_utc(envelope["occurredAt"])))


def handle_ticket_opened(session: Session, envelope: dict) -> None:
    """Consumidor de TicketOpened.v1: inicia a resolução com o prazo publicado por Support.

    O prazo é o `dueAt` do chamado, nunca o instante do despacho: atraso ou
    reentrega da outbox não estende o SLA. Chamado pendente de elegibilidade
    (sem `dueAt`) recebe prazo operacional provisório de 24 h contado da
    abertura, substituído na reconciliação.
    """
    payload = envelope["payload"]
    if payload.get("dueAt"):
        due_at = parse_utc(payload["dueAt"])
    else:
        opened_at = parse_utc(payload.get("openedAt") or envelope["occurredAt"])
        due_at = opened_at + timedelta(hours=payload.get("slaHours") or 24)
    _start(session, envelope, "TICKET_RESOLUTION", "ticketId", due_at)


def handle_ticket_entitlement_reconciled(session: Session, envelope: dict) -> None:
    """Consumidor de TicketEntitlementReconciled.v1: ajusta o prazo ou cancela a resolução."""
    payload = envelope["payload"]
    process = _find_process(session, "TICKET_RESOLUTION", payload["ticketId"])
    if not process:
        return
    if payload["status"] == "OPEN":
        process.due_at = parse_utc(payload["dueAt"])
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


def process_summary(session: Session) -> dict:
    """Processos gravados e em andamento (não finais), sem o limite da listagem (#73)."""
    counts = dict(session.execute(select(ProcessInstance.state, func.count()).group_by(ProcessInstance.state)).all())
    return {"total": sum(counts.values()), "running": sum(n for state, n in counts.items() if state not in FINAL_PROCESS_STATES)}


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


def _locked_process(session: Session, process_id: str) -> ProcessInstance | None:
    """Lê o processo com bloqueio de linha (PostgreSQL) para serializar o agregado das tarefas."""
    return session.get(ProcessInstance, process_id, with_for_update=True, populate_existing=True)


def create_task(session: Session, process_id: str, title: str, owner: str, correlation_id: str) -> ProcessTask:
    """Cria tarefa em processo não encerrado, com o prazo do processo, e registra auditoria."""
    process = _locked_process(session, process_id)
    if not process:
        raise NotFoundError("Processo não encontrado")
    ensure_process_open(process.state)
    task = ProcessTask(process_id=process.process_id, title=title, owner=owner, due_at=process.due_at)
    session.add(task)
    session.flush()
    audit(session, correlation_id, "workflow", "create_task", "success", task.task_id, processId=process.process_id)
    session.commit()
    return task


def change_task(session: Session, task_id: str, state: str, owner: str | None, correlation_id: str) -> ProcessTask:
    """Altera estado ou responsável da tarefa e recalcula o processo; repetição exata não tem efeito."""
    task = session.get(ProcessTask, task_id)
    if not task:
        raise NotFoundError("Tarefa não encontrada")
    process = _locked_process(session, task.process_id)
    session.refresh(task)
    ensure_process_open(process.state)
    if not task_change_needed(task.state, task.owner, state, owner):
        session.rollback()
        return task
    previous_state, previous_owner = task.state, task.owner
    task.state = state
    task.owner = owner or task.owner
    process_before = process.state
    process.state = aggregate_process_state(process.state, [t.state for t in _tasks(session, process)])
    audit(session, correlation_id, "workflow", "change_task", "success", task.task_id, processId=process.process_id,
          fromState=previous_state, toState=task.state, ownerChanged=task.owner != previous_owner)
    if process.state != process_before:
        audit(session, correlation_id, "workflow", "change_process_state", "success", process.process_id,
              fromState=process_before, toState=process.state)
    session.commit()
    return task
