from archcorp.exceptions import InvalidStateError


FINAL_TASK_STATES = {"DONE", "CANCELLED"}
FINAL_PROCESS_STATES = {"COMPLETED", "CANCELLED"}


def require_editable_task(state: str, process_state: str) -> None:
    if state in FINAL_TASK_STATES or process_state in FINAL_PROCESS_STATES:
        raise InvalidStateError("Tarefa ou processo encerrado não pode ser alterado")


def process_state_for_tasks(states: list[str]) -> str:
    if states and all(state == "DONE" for state in states):
        return "COMPLETED"
    if states and all(state in FINAL_TASK_STATES for state in states):
        return "CANCELLED"
    if "IN_PROGRESS" in states:
        return "IN_PROGRESS"
    return "STARTED"
