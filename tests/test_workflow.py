import pytest
from sqlalchemy import select

from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import AuditLog
from archcorp.workflow.domain import process_state_for_tasks


@pytest.mark.parametrize(("states", "expected"), [
    (["DONE", "CANCELLED"], "CANCELLED"),
    (["DONE", "OPEN"], "STARTED"),
    (["DONE", "IN_PROGRESS"], "IN_PROGRESS"),
    (["DONE", "DONE"], "COMPLETED"),
])
def test_estado_agregado_das_tarefas(states, expected):
    assert process_state_for_tasks(states) == expected


@pytest.fixture
def process(client, admin_headers, integrated_contract):
    _, contract = integrated_contract
    activated = client.post(f"/api/v1/contracts/{contract['contractId']}/activate",
                            headers={**admin_headers, "Idempotency-Key": "workflow-activation"})
    assert activated.status_code == 200
    assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json()["processed"] == 1
    return client.get("/api/v1/workflow/processes", headers=admin_headers).json()[0]


def tasks(client, headers, process):
    return client.get("/api/v1/workflow/tasks", headers=headers,
                      params={"processId": process["processId"]}).json()


def test_cancelar_todas_as_tarefas_encerra_processo(client, admin_headers, process):
    task = tasks(client, admin_headers, process)[0]
    path = f"/api/v1/workflow/tasks/{task['taskId']}"
    assert client.patch(path, headers=admin_headers, json={"state": "CANCELLED"}).status_code == 200
    stored = client.get(f"/api/v1/workflow/processes/{process['processId']}", headers=admin_headers).json()
    assert stored["state"] == "CANCELLED"
    assert client.patch(path, headers=admin_headers, json={"state": "CANCELLED"}).status_code == 200
    assert client.post("/api/v1/workflow/tasks", headers=admin_headers, json={
        "processId": process["processId"], "title": "Não deve ser criada",
    }).status_code == 409


@pytest.mark.parametrize("terminal", ["DONE", "CANCELLED"])
def test_tarefa_final_nao_reabre_em_processo_ativo(client, admin_headers, process, terminal):
    original = tasks(client, admin_headers, process)[0]
    assert client.post("/api/v1/workflow/tasks", headers=admin_headers, json={
        "processId": process["processId"], "title": "Segunda tarefa",
    }).status_code == 201
    path = f"/api/v1/workflow/tasks/{original['taskId']}"
    assert client.patch(path, headers=admin_headers, json={"state": terminal}).status_code == 200
    response = client.patch(path, headers=admin_headers, json={"state": "OPEN"})
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_STATE"
    assert next(t for t in tasks(client, admin_headers, process) if t["taskId"] == original["taskId"])["state"] == terminal


def test_tarefas_prazo_responsavel_conclusao_e_auditoria(client, admin_headers, process):
    original = tasks(client, admin_headers, process)[0]
    created = client.post("/api/v1/workflow/tasks", headers=admin_headers, json={
        "processId": process["processId"], "title": "Conferir retirada", "owner": "Equipe sintética",
    })
    assert created.status_code == 201
    extra = created.json()
    assert extra["dueAt"] == process["dueAt"] == original["dueAt"]
    path = f"/api/v1/workflow/tasks/{extra['taskId']}"
    changed = client.patch(path, headers=admin_headers, json={"state": "IN_PROGRESS", "owner": "Equipe de pátio"})
    assert changed.json()["owner"] == "Equipe de pátio"
    process_path = f"/api/v1/workflow/processes/{process['processId']}"
    assert client.get(process_path, headers=admin_headers).json()["state"] == "IN_PROGRESS"
    for task in [original, extra]:
        assert client.patch(f"/api/v1/workflow/tasks/{task['taskId']}", headers=admin_headers, json={"state": "DONE"}).status_code == 200
    assert client.get(process_path, headers=admin_headers).json()["state"] == "COMPLETED"
    assert client.patch(path, headers=admin_headers, json={"state": "DONE"}).status_code == 200
    assert client.patch(path, headers=admin_headers, json={"state": "DONE", "owner": "Outra equipe"}).status_code == 409
    with SessionLocal() as session:
        logs = session.scalars(select(AuditLog).where(AuditLog.module == "workflow", AuditLog.entity_id == extra["taskId"])).all()
        assert [log.operation for log in logs] == ["create_task", "change_task", "change_task"]
        assert all(log.correlation_id == admin_headers["X-Correlation-ID"] for log in logs)


def test_workflow_autorizacao(client, admin_headers, process):
    body = {"processId": process["processId"], "title": "Tarefa protegida"}
    assert client.post("/api/v1/workflow/tasks", json=body).status_code == 401
    assert client.post("/api/v1/workflow/tasks", headers={"Authorization": "Bearer demo-support"}, json=body).status_code == 403
    assert client.post("/api/v1/workflow/tasks", headers={"Authorization": "Bearer demo-operations"}, json=body).status_code == 201
