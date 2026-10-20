"""Estados finais, agregado, auditoria e prazos do Workflow (plano de conclusão, pacote C; #59)."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from archcorp.exceptions import ConflictError, InvalidStateError
from archcorp.infrastructure.db import engine
from archcorp.workflow import domain, service
from archcorp.workflow.models import ProcessInstance


@pytest.fixture
def onboarding(client, admin_headers, integrated_contract):
    """Processo de preparação aberto pela ativação, com a tarefa inicial e uma tarefa extra."""
    _, contract = integrated_contract
    client.post(f"/api/v1/contracts/{contract['contractId']}/activate", headers={**admin_headers, "Idempotency-Key": "wf-activate"})
    assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json()["failed"] == 0
    process = next(p for p in client.get("/api/v1/workflow/processes", headers=admin_headers).json() if p["referenceId"] == contract["contractId"])
    first = client.get("/api/v1/workflow/tasks", headers=admin_headers, params={"processId": process["processId"]}).json()[0]
    second = client.post("/api/v1/workflow/tasks", headers=admin_headers, json={"processId": process["processId"], "title": "Conferir documentos"})
    assert second.status_code == 201, second.text
    return process, first, second.json()


def _process(client, headers, process_id):
    return client.get(f"/api/v1/workflow/processes/{process_id}", headers=headers).json()


def _patch(client, headers, task_id, **body):
    return client.patch(f"/api/v1/workflow/tasks/{task_id}", headers=headers, json=body)


def test_tarefa_final_nao_reabre_enquanto_outra_mantem_o_processo_ativo(client, admin_headers, onboarding):
    process, first, second = onboarding
    assert _patch(client, admin_headers, first["taskId"], state="DONE").status_code == 200
    assert _process(client, admin_headers, process["processId"])["state"] != "COMPLETED"

    reopened = _patch(client, admin_headers, first["taskId"], state="OPEN")
    assert reopened.status_code == 409
    assert reopened.json()["code"] == "INVALID_STATE"
    cancelled = _patch(client, admin_headers, first["taskId"], state="CANCELLED")
    assert cancelled.status_code == 409
    task = client.get("/api/v1/workflow/tasks", headers=admin_headers, params={"processId": process["processId"]}).json()
    assert {t["taskId"]: t["state"] for t in task}[first["taskId"]] == "DONE"


def test_tarefa_final_nao_troca_de_responsavel_e_repeticao_exata_nao_tem_efeito(client, admin_headers, onboarding):
    _, first, _ = onboarding
    done = _patch(client, admin_headers, first["taskId"], state="DONE", owner="Equipe de pátio")
    assert done.status_code == 200
    headers = {**admin_headers, "X-Correlation-ID": "22222222-2222-4222-8222-222222222222"}

    assert _patch(client, headers, first["taskId"], state="DONE", owner="Outra equipe").status_code == 409
    repeated = _patch(client, headers, first["taskId"], state="DONE", owner="Equipe de pátio")
    assert repeated.status_code == 200
    assert repeated.json() == done.json()
    assert _patch(client, headers, first["taskId"], state="DONE").status_code == 200
    trace = client.get(f"/api/v1/operations/{headers['X-Correlation-ID']}", headers=admin_headers).json()
    assert [a for a in trace["audit"] if a["operation"] == "change_task"] == []


def test_todas_concluidas_completam_e_processo_final_nao_recebe_tarefa(client, admin_headers, onboarding):
    process, first, second = onboarding
    _patch(client, admin_headers, first["taskId"], state="IN_PROGRESS")
    assert _process(client, admin_headers, process["processId"])["state"] == "IN_PROGRESS"
    _patch(client, admin_headers, first["taskId"], state="DONE")
    assert _patch(client, admin_headers, second["taskId"], state="DONE").status_code == 200
    assert _process(client, admin_headers, process["processId"])["state"] == "COMPLETED"

    late = client.post("/api/v1/workflow/tasks", headers=admin_headers, json={"processId": process["processId"], "title": "Tarefa tardia"})
    assert late.status_code == 409
    assert late.json()["code"] == "CONFLICT"
    assert late.json()["detail"] == "Processo encerrado"


def test_todas_finais_com_cancelamento_cancelam_o_processo(client, admin_headers, onboarding):
    process, first, second = onboarding
    _patch(client, admin_headers, first["taskId"], state="DONE")
    assert _patch(client, admin_headers, second["taskId"], state="CANCELLED").status_code == 200
    assert _process(client, admin_headers, process["processId"])["state"] == "CANCELLED"
    assert _patch(client, admin_headers, second["taskId"], state="OPEN").json()["code"] == "CONFLICT"


def test_criacao_e_transicao_sao_auditadas(client, admin_headers, onboarding):
    process, first, second = onboarding
    headers = {**admin_headers, "X-Correlation-ID": "33333333-3333-4333-8333-333333333333"}
    created = client.post("/api/v1/workflow/tasks", headers=headers, json={"processId": process["processId"], "title": "Vistoria"}).json()
    for task in (first, second, created):
        _patch(client, headers, task["taskId"], state="DONE")
    audit = client.get(f"/api/v1/operations/{headers['X-Correlation-ID']}", headers=admin_headers).json()["audit"]
    operations = [(a["operation"], a["entityId"]) for a in audit]
    assert ("create_task", created["taskId"]) in operations
    assert sum(1 for op, _ in operations if op == "change_task") == 3
    assert ("change_process_state", process["processId"]) in operations


def test_preparacao_vence_72h_apos_a_ativacao_mesmo_com_despacho_atrasado():
    activated = datetime(2026, 10, 1, 9, 30, tzinfo=timezone.utc)
    envelope = {
        "eventId": "e1", "eventType": "ContractActivated.v1", "occurredAt": "2026-10-01T09:30:00Z", "correlationId": "c1",
        "payload": {"contractId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "customerId": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"},
    }
    with Session(engine) as session:
        service.handle_contract_activated(session, envelope)  # despachado dias depois da ativação
        session.commit()
        process = session.scalar(select(ProcessInstance).where(ProcessInstance.reference_id == envelope["payload"]["contractId"]))
        assert domain.parse_utc(process.due_at.isoformat()) == activated + timedelta(hours=72)


@pytest.mark.parametrize(("states", "expected"), [
    (["DONE", "DONE"], "COMPLETED"),
    (["DONE", "CANCELLED"], "CANCELLED"),
    (["CANCELLED"], "CANCELLED"),
    (["DONE", "IN_PROGRESS"], "IN_PROGRESS"),
    (["DONE", "OPEN"], "STARTED"),
    ([], "STARTED"),
])
def test_agregado_do_processo(states, expected):
    assert domain.aggregate_process_state("STARTED", states) == expected


def test_politica_de_alteracao_de_tarefa():
    assert domain.task_change_needed("OPEN", "operations", "IN_PROGRESS", None) is True
    assert domain.task_change_needed("OPEN", "operations", "OPEN", "Equipe") is True
    assert domain.task_change_needed("DONE", "operations", "DONE", None) is False
    assert domain.task_change_needed("DONE", "operations", "DONE", "operations") is False
    for target, owner in (("OPEN", None), ("CANCELLED", None), ("DONE", "Equipe")):
        with pytest.raises(InvalidStateError):
            domain.task_change_needed("DONE", "operations", target, owner)
    with pytest.raises(ConflictError):
        domain.ensure_process_open("COMPLETED")
