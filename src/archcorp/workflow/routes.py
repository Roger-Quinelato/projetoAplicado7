from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.infrastructure.db import get_session
from archcorp.observability import correlation_id_var
from archcorp.schemas import EXAMPLE_CONTRACT_ID, EXAMPLE_CUSTOMER_ID
from archcorp.security import require_roles
from archcorp.workflow import service
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
PROCESS_CLOSED = {409: {"description": "Processo concluído ou cancelado (`CONFLICT`)."}}
# Mesmo status 409 de PROCESS_CLOSED; o código `INVALID_STATE` distingue a tarefa final.
TASK_FINAL = {409: {"description": "Processo concluído ou cancelado (`CONFLICT`) ou tarefa concluída ou cancelada (`INVALID_STATE`)."}}


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


class ProcessSummaryResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"total": 250, "running": 40}]})

    total: int = Field(description="Processos gravados, em qualquer estado.")
    running: int = Field(description="Processos fora dos estados finais COMPLETED e CANCELLED.")


@router.get("/processes/summary", response_model=ProcessSummaryResponse, dependencies=[Depends(require_roles("operations", "support", "contracts", "admin"))])
def process_summary(session: Session = Depends(get_session)) -> dict:
    """Processos gravados e em andamento, sem o limite de 200 da listagem; mudança aditiva na v1 (#73)."""
    return service.process_summary(session)


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
    """Cria tarefa em processo não encerrado, com o prazo do processo; a criação é auditada."""
    return task_data(service.create_task(session, str(body.processId), body.title, body.owner, correlation_id_var.get()))


@router.patch("/tasks/{task_id}", response_model=TaskResponse, responses={404: {"description": "Tarefa não encontrada."}, **PROCESS_CLOSED, **TASK_FINAL}, dependencies=[Depends(require_roles("operations", "admin"))])
def change_task(task_id: UUID, body: TaskChange, session: Session = Depends(get_session)) -> dict:
    """Altera estado ou responsável da tarefa e recalcula o processo; tarefa concluída ou cancelada é final e repetir o estado e o responsável vigentes não tem efeito. O processo é concluído quando todas as tarefas terminam e cancelado quando todas são finais com algum cancelamento."""
    return task_data(service.change_task(session, str(task_id), body.state, body.owner, correlation_id_var.get()))
