"""Revisão cruzada de QUA-05 (independente): comportamento de POST e PATCH de /workflow/tasks (SQLite)."""
from dad_common import H, activate, customer, dispatch, draft, setup

setup("rev_qua05.db")
from fastapi.testclient import TestClient  # noqa: E402

from archcorp.main import app  # noqa: E402

with TestClient(app) as c:
    cust = customer(c, "tarefa")
    cid = draft(c, cust, "REV05-D").json()["contractId"]
    activate(c, cid, "REV05-A")
    dispatch(c)
    proc = next(p for p in c.get("/api/v1/workflow/processes", headers=H).json() if p["referenceId"] == cid)
    pid = proc["processId"]
    tarefas = c.get("/api/v1/workflow/tasks", headers=H, params={"processId": pid}).json()
    print("GET /workflow/tasks:", len(tarefas), "tarefa(s), estado", tarefas[0]["state"])
    r = c.post("/api/v1/workflow/tasks", headers=H, json={"processId": pid, "title": "Conferir documentos", "owner": "operations"})
    print("POST /workflow/tasks:", r.status_code, r.json().get("state") if r.status_code == 201 else r.text[:80])
    t1 = tarefas[0]["taskId"]
    p1 = c.patch(f"/api/v1/workflow/tasks/{t1}", headers=H, json={"state": "DONE"})
    print("PATCH t1 -> DONE:", p1.status_code, p1.json().get("state"))
    p2 = c.patch(f"/api/v1/workflow/tasks/{t1}", headers=H, json={"state": "OPEN"})
    print("PATCH t1 DONE -> OPEN (sem validação de transição):", p2.status_code, p2.json().get("state"))
    p3 = c.patch("/api/v1/workflow/tasks/00000000-0000-4000-8000-000000000000", headers=H, json={"state": "DONE"})
    print("PATCH tarefa inexistente:", p3.status_code)
    c.post(f"/api/v1/contracts/{cid}/close", headers=H, json={})
    print("estado do processo após encerrar o contrato:",
          next(p for p in c.get("/api/v1/workflow/processes", headers=H).json() if p["processId"] == pid)["state"])
    r4 = c.post("/api/v1/workflow/tasks", headers=H, json={"processId": pid, "title": "Tarefa tardia"})
    print("POST em processo encerrado:", r4.status_code)
