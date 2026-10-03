from harness import *
from archcorp.config import settings
def ticket(c, cust, contract_id, key, cat="OUTAGE", desc="Pane sintética"):
    return c.post("/api/v1/support/tickets", headers={**H, "Idempotency-Key": key}, json={"customerId": cust["customerId"], "contractId": contract_id, "serviceCode": "RENTAL-FLEX", "category": cat, "description": desc})
with client() as c:
    cust = customer(c); d = draft(c, cust, "T").json(); activate(c, d["contractId"], "T-A"); dispatch(c)
    show("entitlement ativo", c.get(f"/api/v1/contracts/{d['contractId']}/entitlement", headers=H, params={"customerId": cust["customerId"], "serviceCode": "RENTAL-FLEX"}))
    t1 = show("F3 abre chamado", ticket(c, cust, d["contractId"], "T1"))
    show("F3 mesma chave, descricao diferente", ticket(c, cust, d["contractId"], "T1", desc="Outra descrição totalmente diferente"))
    show("F3 mesma chave, categoria diferente", ticket(c, cust, d["contractId"], "T1", cat="QUESTION"))
    show("dispatch", dispatch(c))
    show("GET chamado (dueAt apos releitura do banco)", c.get(f"/api/v1/support/tickets/{t1['ticketId']}", headers=H))
    procs = show("processos", c.get("/api/v1/workflow/processes", headers=H))
    show("contrato inexistente", ticket(c, cust, "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "T2"))
    dd = draft(c, cust, "T-D", starts="2031-01-01").json()
    show("contrato em DRAFT", ticket(c, cust, dd["contractId"], "T3"))
    other = customer(c)
    show("cliente diferente do contrato", ticket(c, other, d["contractId"], "T4"))
    show("serviceCode vazio", c.post("/api/v1/support/tickets", headers={**H, "Idempotency-Key": "T5"}, json={"customerId": cust["customerId"], "contractId": d["contractId"], "serviceCode": "", "category": "OUTAGE", "description": "x y z"}))
    # Adaptador indisponivel com contrato inexistente
    settings.contract_adapter_available = False
    tp = show("pendente com contrato INEXISTENTE", ticket(c, cust, "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", "T6"))
    settings.contract_adapter_available = True
    show("dispatch (workflow para chamado pendente)", dispatch(c))
    show("resolver chamado pendente", c.post(f"/api/v1/support/tickets/{tp['ticketId']}/resolve", headers=H))
    show("reconciliar pendente inexistente", c.post(f"/api/v1/support/tickets/{tp['ticketId']}/reconcile", headers=H))
    show("dispatch", dispatch(c))
    show("reconciliar de novo", c.post(f"/api/v1/support/tickets/{tp['ticketId']}/reconcile", headers=H))
    show("atribuir rejeitado", c.post(f"/api/v1/support/tickets/{tp['ticketId']}/assign", headers=H, json={"owner": "Equipe"}))
    # transicoes de chamado
    show("resolver T1", c.post(f"/api/v1/support/tickets/{t1['ticketId']}/resolve", headers=H))
    show("resolver T1 de novo", c.post(f"/api/v1/support/tickets/{t1['ticketId']}/resolve", headers=H))
    show("reabrir? (sem rota) atribuir resolvido", c.post(f"/api/v1/support/tickets/{t1['ticketId']}/assign", headers=H, json={"owner": "Equipe"}))
    show("dispatch", dispatch(c))
    show("processos", c.get("/api/v1/workflow/processes", headers=H))
    # Workflow: transicoes de tarefa
    t2 = show("F3 novo chamado T7", ticket(c, cust, d["contractId"], "T7")); dispatch(c)
    p = [x for x in c.get("/api/v1/workflow/processes", headers=H).json() if x["referenceId"] == t2["ticketId"]][0]
    task = c.get("/api/v1/workflow/tasks", headers=H, params={"processId": p["processId"]}).json()[0]
    show("tarefa OPEN->DONE", c.patch(f"/api/v1/workflow/tasks/{task['taskId']}", headers=H, json={"state": "DONE"}))
    show("processo apos DONE", c.get(f"/api/v1/workflow/processes/{p['processId']}", headers=H))
    show("tarefa DONE->OPEN (processo COMPLETED)", c.patch(f"/api/v1/workflow/tasks/{task['taskId']}", headers=H, json={"state": "OPEN"}))
    show("chamado T7 ainda OPEN apos processo COMPLETED?", c.get(f"/api/v1/support/tickets/{t2['ticketId']}", headers=H))
    t3 = show("F3 novo chamado T8", ticket(c, cust, d["contractId"], "T8")); dispatch(c)
    p3 = [x for x in c.get("/api/v1/workflow/processes", headers=H).json() if x["referenceId"] == t3["ticketId"]][0]
    task3 = c.get("/api/v1/workflow/tasks", headers=H, params={"processId": p3["processId"]}).json()[0]
    show("tarefa OPEN->CANCELLED", c.patch(f"/api/v1/workflow/tasks/{task3['taskId']}", headers=H, json={"state": "CANCELLED"}))
    show("tarefa CANCELLED->IN_PROGRESS", c.patch(f"/api/v1/workflow/tasks/{task3['taskId']}", headers=H, json={"state": "IN_PROGRESS"}))
    show("tarefa IN_PROGRESS->OPEN", c.patch(f"/api/v1/workflow/tasks/{task3['taskId']}", headers=H, json={"state": "OPEN"}))
    show("processo p3", c.get(f"/api/v1/workflow/processes/{p3['processId']}", headers=H))
    show("nova tarefa no processo p3", c.post("/api/v1/workflow/tasks", headers=H, json={"processId": p3["processId"], "title": "Tarefa extra"}))
    show("nova tarefa repetida (sem idempotencia)", c.post("/api/v1/workflow/tasks", headers=H, json={"processId": p3["processId"], "title": "Tarefa extra"}))
    # Encerramento do contrato: efeito sobre chamado aberto T8, fatura, processos
    show("encerrar contrato", c.post(f"/api/v1/contracts/{d['contractId']}/close", headers={**H, "Idempotency-Key": "CLS"}, json={"reason": "Fim"}))
    show("encerrar de novo sem chave", c.post(f"/api/v1/contracts/{d['contractId']}/close", headers=H, json={"reason": "Fim"}))
    show("encerrar de novo outra chave", c.post(f"/api/v1/contracts/{d['contractId']}/close", headers={**H, "Idempotency-Key": "CLS2"}, json={"reason": "Outro motivo"}))
    show("encerrar mesma chave outro motivo", c.post(f"/api/v1/contracts/{d['contractId']}/close", headers={**H, "Idempotency-Key": "CLS"}, json={"reason": "Outro motivo"}))
    show("dispatch", dispatch(c))
    show("chamado T8 apos encerramento", c.get(f"/api/v1/support/tickets/{t3['ticketId']}", headers=H))
    show("resolver T8 apos encerramento", c.post(f"/api/v1/support/tickets/{t3['ticketId']}/resolve", headers=H))
    show("novo chamado em contrato encerrado", ticket(c, cust, d["contractId"], "T9"))
    show("processos finais", c.get("/api/v1/workflow/processes", headers=H))
    show("fatura do contrato encerrado", c.get("/api/v1/finance/invoices", headers=H))
