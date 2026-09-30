from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.infrastructure.db import get_session
from archcorp.schemas import EXAMPLE_CONTRACT_ID, EXAMPLE_CUSTOMER_ID
from archcorp.security import require_roles
from archcorp.workflow.models import ProcessInstance, ProcessTask


router = APIRouter(prefix="/api/v1/workflow", tags=["Gestão de processos"])


EXAMPLE_PROCESS = {
    "processId": "13131313-1313-4131-8131-131313131313",
    "processType": "ONBOARDING",
    "referenceId": EXAMPLE_CONTRACT_ID,
    "customerId": EXAMPLE_CUSTOMER_ID,
    "state": "STARTED",
    "owner": "operations",
    "dueAt": "2026-10-04T10:00:00Z",
}
EXAMPLE_TASK = {
    "taskId": "14141414-1414-4141-8141-141414141414",
    "processId": EXAMPLE_PROCESS["processId"],
    "title": "Executar onboarding",
    "state": "OPEN",
    "owner": "operations",
    "dueAt": "2026-10-04T10:00:00Z",
}
PROCESS_CLOSED = {409: {"description": "Processo concluído ou cancelado."}}


class TaskInput(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"processId": EXAMPLE_PROCESS["processId"], "title": "Conferir documentos da retirada", "owner": "operations"}]})

    processId: UUID
    title: str = Field(min_length=3, max_length=150)
    owner: str = Field(default="operations", min_length=2, max_length=80)


class TaskChange(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"state": "IN_PROGRESS", "owner": "Equipe de pátio"}]})

    state: Literal["OPEN", "IN_PROGRESS", "DONE", "CANCELLED"]
    owner: str | None = Field(default=None, min_length=2, max_length=80)


class ProcessResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_PROCESS]})

    processId: UUID
    processType: str
    referenceId: UUID
    customerId: UUID
    state: str
    owner: str
    dueAt: datetime | None


class TaskResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [EXAMPLE_TASK]})

    taskId: UUID
    processId: UUID
    title: str
    state: Literal["OPEN", "IN_PROGRESS", "DONE", "CANCELLED"]
    owner: str
    dueAt: datetime | None


def process_data(item: ProcessInstance) -> dict:
    """Serializa o processo no formato da API."""
    return {"processId": item.process_id, "processType": item.process_type,
            "referenceId": item.reference_id, "customerId": item.customer_id,
            "state": item.state, "owner": item.owner,
            "dueAt": item.due_at.isoformat() if item.due_at else None}


def task_data(item: ProcessTask) -> dict:
    """Serializa a tarefa no formato da API."""
    return {"taskId": item.task_id, "processId": item.process_id,
            "title": item.title, "state": item.state, "owner": item.owner,
            "dueAt": item.due_at.isoformat() if item.due_at else None}


@router.get("/processes", response_model=list[ProcessResponse], dependencies=[Depends(require_roles("operations", "support", "contracts", "admin"))])
def list_processes(session: Session = Depends(get_session)) -> list[dict]:
    """Lista até 200 processos."""
    return [process_data(x) for x in session.scalars(select(ProcessInstance).order_by(ProcessInstance.process_id).limit(200))]


@router.get("/processes/{process_id}", response_model=ProcessResponse, responses={404: {"description": "Processo não encontrado."}}, dependencies=[Depends(require_roles("operations", "support", "contracts", "admin"))])
def get_process(process_id: UUID, session: Session = Depends(get_session)) -> dict:
    """Consulta um processo."""
    item = session.get(ProcessInstance, str(process_id))
    if not item:
        raise HTTPException(404, "Processo não encontrado")
    return process_data(item)


@router.get("/tasks", response_model=list[TaskResponse], dependencies=[Depends(require_roles("operations", "support", "contracts", "admin"))])
def list_tasks(processId: UUID | None = None, session: Session = Depends(get_session)) -> list[dict]:
    """Lista até 200 tarefas, com filtro opcional por processo."""
    query = select(ProcessTask).order_by(ProcessTask.task_id).limit(200)
    if processId:
        query = query.where(ProcessTask.process_id == str(processId))
    return [task_data(x) for x in session.scalars(query)]


@router.post("/tasks", status_code=201, response_model=TaskResponse, responses={404: {"description": "Processo não encontrado."}, **PROCESS_CLOSED}, dependencies=[Depends(require_roles("operations", "admin"))])
def create_task(body: TaskInput, session: Session = Depends(get_session)) -> dict:
    """Cria tarefa em processo não encerrado, com o prazo do processo."""
    process = session.get(ProcessInstance, str(body.processId))
    if not process:
        raise HTTPException(404, "Processo não encontrado")
    if process.state in {"COMPLETED", "CANCELLED"}:
        raise HTTPException(409, "Processo encerrado")
    item = ProcessTask(process_id=process.process_id, title=body.title,
                       owner=body.owner, due_at=process.due_at)
    session.add(item)
    session.commit()
    return task_data(item)


@router.patch("/tasks/{task_id}", response_model=TaskResponse, responses={404: {"description": "Tarefa não encontrada."}, **PROCESS_CLOSED}, dependencies=[Depends(require_roles("operations", "admin"))])
def change_task(task_id: UUID, body: TaskChange, session: Session = Depends(get_session)) -> dict:
    """Altera estado ou responsável da tarefa; o processo é concluído quando todas as tarefas terminam."""
    item = session.get(ProcessTask, str(task_id))
    if not item:
        raise HTTPException(404, "Tarefa não encontrada")
    process = session.get(ProcessInstance, item.process_id)
    if process.state in {"COMPLETED", "CANCELLED"}:
        raise HTTPException(409, "Processo encerrado")
    item.state = body.state
    if body.owner:
        item.owner = body.owner
    tasks = session.scalars(select(ProcessTask).where(ProcessTask.process_id == process.process_id)).all()
    if tasks and all(task.state == "DONE" for task in tasks):
        process.state = "COMPLETED"
    elif body.state == "IN_PROGRESS":
        process.state = "IN_PROGRESS"
    session.commit()
    return task_data(item)
