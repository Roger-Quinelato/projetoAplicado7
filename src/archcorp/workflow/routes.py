from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.infrastructure.db import get_session
from archcorp.security import require_roles
from archcorp.workflow.models import ProcessInstance, ProcessTask


router = APIRouter(prefix="/api/v1/workflow", tags=["Gestão de processos"])


class TaskInput(BaseModel):
    processId: UUID
    title: str = Field(min_length=3, max_length=150)
    owner: str = Field(default="operations", min_length=2, max_length=80)


class TaskChange(BaseModel):
    state: Literal["OPEN", "IN_PROGRESS", "DONE", "CANCELLED"]
    owner: str | None = Field(default=None, min_length=2, max_length=80)


def process_data(item: ProcessInstance) -> dict:
    return {"processId": item.process_id, "processType": item.process_type,
            "referenceId": item.reference_id, "customerId": item.customer_id,
            "state": item.state, "owner": item.owner,
            "dueAt": item.due_at.isoformat() if item.due_at else None}


def task_data(item: ProcessTask) -> dict:
    return {"taskId": item.task_id, "processId": item.process_id,
            "title": item.title, "state": item.state, "owner": item.owner,
            "dueAt": item.due_at.isoformat() if item.due_at else None}


@router.get("/processes", dependencies=[Depends(require_roles("operations", "support", "contracts", "admin"))])
def list_processes(session: Session = Depends(get_session)) -> list[dict]:
    return [process_data(x) for x in session.scalars(select(ProcessInstance).order_by(ProcessInstance.process_id).limit(200))]


@router.get("/processes/{process_id}", dependencies=[Depends(require_roles("operations", "support", "contracts", "admin"))])
def get_process(process_id: UUID, session: Session = Depends(get_session)) -> dict:
    item = session.get(ProcessInstance, str(process_id))
    if not item:
        raise HTTPException(404, "Processo não encontrado")
    return process_data(item)


@router.get("/tasks", dependencies=[Depends(require_roles("operations", "support", "contracts", "admin"))])
def list_tasks(processId: UUID | None = None, session: Session = Depends(get_session)) -> list[dict]:
    query = select(ProcessTask).order_by(ProcessTask.task_id).limit(200)
    if processId:
        query = query.where(ProcessTask.process_id == str(processId))
    return [task_data(x) for x in session.scalars(query)]


@router.post("/tasks", status_code=201, dependencies=[Depends(require_roles("operations", "admin"))])
def create_task(body: TaskInput, session: Session = Depends(get_session)) -> dict:
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


@router.patch("/tasks/{task_id}", dependencies=[Depends(require_roles("operations", "admin"))])
def change_task(task_id: UUID, body: TaskChange, session: Session = Depends(get_session)) -> dict:
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
