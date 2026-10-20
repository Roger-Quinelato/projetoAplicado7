"""Regras do processo e das tarefas operacionais (T16), sem dependência de HTTP, banco ou framework.

Política de tarefas (Q-07, plano de conclusão, pacote C):

- tarefa `DONE` ou `CANCELLED` é final: não muda de estado nem de responsável; repetir exatamente
  o mesmo pedido não tem efeito;
- processo `COMPLETED` ou `CANCELLED` é final e não recebe novas tarefas nem alterações;
- o processo é `COMPLETED` quando todas as tarefas estão `DONE`, `CANCELLED` quando todas são
  finais e ao menos uma foi cancelada, e `IN_PROGRESS` quando alguma tarefa está em andamento.

Prazos são calculados a partir de instantes do fato (`occurredAt`), nunca do relógio do despacho.
"""
from datetime import datetime, timedelta, timezone

from archcorp.exceptions import ConflictError, InvalidStateError


FINAL_TASK_STATES = frozenset({"DONE", "CANCELLED"})
FINAL_PROCESS_STATES = frozenset({"COMPLETED", "CANCELLED"})
# Premissa a validar: a preparação de retirada vence 72 h após a ativação do contrato.
PREPARATION_HOURS = 72


def parse_utc(value: str) -> datetime:
    """Converte um instante ISO 8601 do evento em datetime UTC; sem fuso, é lido como UTC."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def preparation_due(activated_at: datetime) -> datetime:
    """Prazo da preparação de retirada contado da ativação, não do processamento do evento."""
    return activated_at + timedelta(hours=PREPARATION_HOURS)


def ensure_process_open(state: str) -> None:
    """Processo final não recebe tarefas nem alterações (mensagem e código da v1)."""
    if state in FINAL_PROCESS_STATES:
        raise ConflictError("Processo encerrado")


def task_change_needed(current_state: str, current_owner: str, target_state: str, target_owner: str | None) -> bool:
    """Indica se o pedido altera a tarefa; recusa alterar tarefa final.

    Responsável omitido mantém o atual. Repetir o estado e o responsável vigentes não é alteração,
    inclusive em tarefa final.
    """
    owner = target_owner or current_owner
    if target_state == current_state and owner == current_owner:
        return False
    if current_state in FINAL_TASK_STATES:
        raise InvalidStateError("Tarefa concluída ou cancelada não pode ser alterada")
    return True


def aggregate_process_state(current: str, task_states: list[str]) -> str:
    """Estado do processo derivado das tarefas; sem regra aplicável, mantém o estado atual."""
    if task_states and all(state == "DONE" for state in task_states):
        return "COMPLETED"
    if task_states and all(state in FINAL_TASK_STATES for state in task_states):
        return "CANCELLED"
    if any(state == "IN_PROGRESS" for state in task_states):
        return "IN_PROGRESS"
    return current
