"""Experimentos de F-MOD (auditoria de 18/10/2026) sobre a cópia isolada iso-mod, com SQLite e TestClient.

Uso (PYTHONPATH=<ISO>\\src, cwd=<ISO>):
    python exp_mod_fluxos.py principal <db_absoluto>
    python exp_mod_fluxos.py pendente-1 <db_absoluto>   # com CONTRACT_ADAPTER_AVAILABLE=false
    python exp_mod_fluxos.py pendente-2 <db_absoluto>   # sem a variável (adaptador ligado)

Dados sintéticos e tokens de demonstração do próprio repositório (demo-*). Nenhum segredo real.
Cada resultado sai como linha "RESULTADO | rótulo | esperado | observado".
"""
import json
import os
import sys
import uuid
from pathlib import Path

CENARIO = sys.argv[1]
DB = Path(sys.argv[2])
if CENARIO == "principal" and DB.exists():
    DB.unlink()
os.environ["DATABASE_URL"] = "sqlite:///" + DB.as_posix()
os.environ.setdefault("FINANCE_ALLOW_FUTURE_AS_OF", "true")  # simulação local, apenas nesta cópia
os.environ.pop("RABBITMQ_URL", None)

from fastapi.testclient import TestClient  # noqa: E402

from archcorp.main import app  # noqa: E402

ADMIN, OPS, SUP, FIN, CON = "demo-admin", "demo-operations", "demo-support", "demo-finance", "demo-contracts"


def h(token, key=None, corr=None):
    headers = {"Authorization": f"Bearer {token}", "X-Correlation-ID": corr or str(uuid.uuid4())}
    if key:
        headers["Idempotency-Key"] = key
    return headers


def rec(label, expected, observed):
    print(f"RESULTADO | {label} | esperado: {expected} | observado: {observed}", flush=True)


def ops_names(c, corr):
    body = c.get(f"/api/v1/operations/{corr}", headers=h(OPS)).json()
    return [a["operation"] for a in body.get("audit", [])]


def process_of(c, process_type, reference_id):
    procs = c.get("/api/v1/workflow/processes", headers=h(OPS)).json()
    return next((p for p in procs if p["processType"] == process_type and p["referenceId"] == reference_id), None)


def tasks_of(c, process_id):
    return c.get("/api/v1/workflow/tasks", params={"processId": process_id}, headers=h(OPS)).json()


def principal(c):
    tag = uuid.uuid4().hex[:8]
    r = c.post("/api/v1/crm/customers", headers=h(ADMIN), json={
        "name": "Cliente Auditoria MOD", "email": f"mod-{tag}@example.com", "legacyId": f"MOD-{tag}"})
    cust = r.json()["customerId"]
    rec("CRM cria cliente sintético", "201", r.status_code)

    r = c.post("/api/v1/contracts/drafts", headers=h(CON, key=f"mod-draft-{tag}"), json={
        "customerId": cust, "serviceCode": "RENTAL-FLEX", "startsOn": "2026-10-20",
        "billing": {"amount": 2500.00, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8})
    contract = r.json()["contractId"]
    rec("Contracts cria rascunho direto", "201", r.status_code)

    r = c.post(f"/api/v1/contracts/{contract}/activate", headers=h(CON, key=f"mod-act-{tag}"))
    rec("Contracts ativa contrato", "200", r.status_code)
    r = c.post("/api/v1/integration/outbox/dispatch", headers=h(OPS))
    rec("Despacho após ativação", "processed >= 2", r.json())

    inv = c.get("/api/v1/finance/invoices", params={"contractId": contract}, headers=h(FIN)).json()
    initial = next(i for i in inv if i["kind"] == "INITIAL")
    rec("Finance cria fatura INITIAL com vencimento = data UTC do evento + 10 dias", "dueDate 2026-10-30 ou 2026-10-29",
        {"dueDate": initial["dueDate"], "amount": initial["amount"], "status": initial["status"]})
    onboarding = process_of(c, "ONBOARDING", contract)
    rec("Workflow inicia ONBOARDING", "STARTED", onboarding and onboarding["state"])
    task1 = tasks_of(c, onboarding["processId"])[0]["taskId"]

    r = c.post("/api/v1/support/tickets", headers=h(SUP, key=f"mod-tkt-{tag}"), json={
        "customerId": cust, "contractId": contract, "serviceCode": "RENTAL-FLEX", "category": "OUTAGE",
        "description": "Teste de auditoria com dados sintéticos"})
    ticket = r.json()["ticketId"]
    rec("Support abre chamado com contrato ativo", "201 status OPEN", (r.status_code, r.json().get("status")))
    c.post("/api/v1/integration/outbox/dispatch", headers=h(OPS))
    ticket_process = process_of(c, "TICKET_RESOLUTION", ticket)
    rec("Workflow inicia TICKET_RESOLUTION após despacho", "STARTED", ticket_process and ticket_process["state"])
    ttask = tasks_of(c, ticket_process["processId"])[0]["taskId"]

    # AUD-30: transições de tarefa sem máquina de estados (processo de ONBOARDING ainda aberto)
    r = c.post("/api/v1/workflow/tasks", headers=h(OPS), json={
        "processId": onboarding["processId"], "title": "Conferir documentos da retirada", "owner": "operations"})
    task2 = r.json()["taskId"]
    rec("Workflow cria segunda tarefa em processo aberto", "201", r.status_code)
    seq = []
    for state in ("CANCELLED", "IN_PROGRESS", "DONE", "OPEN"):
        r = c.patch(f"/api/v1/workflow/tasks/{task1}", headers=h(OPS), json={"state": state})
        seq.append((state, r.status_code))
    rec("Workflow aceita CANCELLED->IN_PROGRESS->DONE->OPEN (sem máquina de estados)",
        "409 para transição inválida se houvesse máquina", seq)

    r = c.patch(f"/api/v1/workflow/tasks/{ttask}", headers=h(OPS), json={"state": "DONE"})
    rec("Tarefa única de TICKET_RESOLUTION concluída", "200", r.status_code)
    tp = process_of(c, "TICKET_RESOLUTION", ticket)
    tk = c.get(f"/api/v1/support/tickets/{ticket}", headers=h(SUP)).json()
    rec("AUD-30 parte 2: processo concluído não propaga ao chamado", "chamado deixa de ficar OPEN",
        {"processo": tp["state"], "chamado": tk["status"]})

    # AUD-29: pagamento auditado e inadimplência persistida e auditada
    corr_pay = str(uuid.uuid4())
    r = c.post(f"/api/v1/finance/invoices/{initial['invoiceId']}/payments", headers=h(FIN, corr=corr_pay), json={
        "amount": 100.00, "currency": "BRL", "reference": f"SIM-{tag}"})
    rec("Finance registra pagamento parcial simulado", "201", r.status_code)
    rec("AUD-29: pagamento aparece na trilha da correlação", "record_simulated_payment presente",
        "record_simulated_payment" in ops_names(c, corr_pay))
    corr_od = str(uuid.uuid4())
    r = c.post("/api/v1/finance/invoices/overdue-check", headers=h(FIN, corr=corr_od), json={"asOf": "2026-12-01"})
    marked = r.json().get("markedOverdue", [])
    rec("AUD-29: verificação de vencimento marca inadimplência", "fatura INITIAL marcada",
        {"status": r.status_code, "marcada": initial["invoiceId"] in marked})
    rec("AUD-29: inadimplência aparece na trilha", "mark_invoice_overdue presente",
        "mark_invoice_overdue" in ops_names(c, corr_od))
    r = c.post("/api/v1/finance/invoices/overdue-check", headers=h(FIN, corr=str(uuid.uuid4())), json={"asOf": "2026-12-01"})
    rec("AUD-29: repetição não marca de novo", "markedOverdue vazio e alreadyOverdue >= 1",
        {"marcadas": r.json().get("markedOverdue"), "jaRegistradas": r.json().get("alreadyOverdue")})

    # AUD-28: encerramento propagado a Finance e Support
    r = c.post(f"/api/v1/contracts/{contract}/close", headers=h(CON), json={"endsOn": "2026-12-15", "reason": "Devolução do veículo"})
    rec("Contracts encerra contrato", "200", r.status_code)
    c.post("/api/v1/integration/outbox/dispatch", headers=h(OPS))
    kinds = sorted((i["kind"], i["amount"]) for i in c.get("/api/v1/finance/invoices", params={"contractId": contract}, headers=h(FIN)).json())
    rec("AUD-28: Finance emite fatura FINAL após ContractClosed", "FINAL presente", kinds)
    onboarding_after = process_of(c, "ONBOARDING", contract)
    tasks_after = [(t["title"][:20], t["state"]) for t in tasks_of(c, onboarding_after["processId"])]
    rec("AUD-28: preparação de retirada concluída com tarefas canceladas", "COMPLETED com tarefas CANCELLED",
        {"processo": onboarding_after["state"], "tarefas": tasks_after})
    tk = c.get(f"/api/v1/support/tickets/{ticket}", headers=h(SUP)).json()
    rec("AUD-28: chamado do contrato encerrado continua OPEN", "OPEN",
        tk["status"])
    r = c.post(f"/api/v1/support/tickets/{ticket}/resolve", headers=h(SUP))
    rec("AUD-28: chamado do contrato encerrado ainda é resolvível", "409 ou bloqueio por encerramento", r.status_code)

    # AUD-45 e 404 x 422: cliente inexistente em reserva e em rascunho direto
    unknown = str(uuid.uuid4())
    r = c.post("/api/v1/contracts/reservations", headers=h(CON), json={
        "customerId": unknown, "vehicleGroup": "SUV", "protectionCode": "BASICA", "serviceCode": "RENTAL-FLEX",
        "startsOn": "2026-11-02", "endsOn": "2026-11-05", "amount": 750.00, "currency": "BRL",
        "billingCycle": "ONCE", "slaHours": 8})
    rec("Cliente inexistente em RESERVA", "404 (divergente do rascunho?)", (r.status_code, r.json().get("detail")))
    r = c.post("/api/v1/contracts/drafts", headers=h(CON, key=f"mod-ghost-{tag}"), json={
        "customerId": unknown, "serviceCode": "RENTAL-FLEX", "startsOn": "2026-11-02",
        "billing": {"amount": 750.00, "currency": "BRL", "cycle": "ONCE"}, "slaHours": 8})
    rec("Cliente inexistente em RASCUNHO direto", "422 (divergente da reserva?)", (r.status_code, r.json().get("detail")))


def pendente_1(c):
    tag = uuid.uuid4().hex[:8]
    unknown_contract, unknown_customer = str(uuid.uuid4()), str(uuid.uuid4())
    r = c.post("/api/v1/support/tickets", headers=h(SUP, key=f"mod-pend-{tag}"), json={
        "customerId": unknown_customer, "contractId": unknown_contract, "serviceCode": "RENTAL-FLEX",
        "category": "OUTAGE", "description": "Chamado pendente sintético"})
    body = r.json()
    rec("AUD-45: chamado com contrato e cliente inexistentes (Contracts indisponível)", "201 PENDING_ENTITLEMENT",
        (r.status_code, body.get("status"), body.get("slaStatus"), body.get("priority")))
    c.post("/api/v1/integration/outbox/dispatch", headers=h(OPS))
    proc = process_of(c, "TICKET_RESOLUTION", body["ticketId"])
    rec("AUD-45: processo de resolução criado para contrato inexistente", "STARTED com prazo de 24 h",
        {"estado": proc and proc["state"], "prazo": proc and proc["dueAt"], "abertura": body.get("openedAt")})
    (DB.parent / "mod_pendente.json").write_text(json.dumps({"ticketId": body["ticketId"], "processId": proc["processId"]}), encoding="utf-8")


def pendente_2(c):
    data = json.loads((DB.parent / "mod_pendente.json").read_text(encoding="utf-8"))
    r = c.post(f"/api/v1/support/tickets/{data['ticketId']}/reconcile", headers=h(SUP))
    rec("AUD-45: reconciliação com Contracts disponível rejeita contrato inexistente", "200 REJECTED_ENTITLEMENT",
        (r.status_code, r.json().get("status")))
    c.post("/api/v1/integration/outbox/dispatch", headers=h(OPS))
    proc = c.get(f"/api/v1/workflow/processes/{data['processId']}", headers=h(OPS)).json()
    rec("AUD-45: processo pendente é cancelado após reconciliação (mitigação)", "CANCELLED",
        proc.get("state"))


with TestClient(app) as client:
    {"principal": principal, "pendente-1": pendente_1, "pendente-2": pendente_2}[CENARIO](client)
print(f"FIM | cenario={CENARIO} | db={DB.name}", flush=True)
