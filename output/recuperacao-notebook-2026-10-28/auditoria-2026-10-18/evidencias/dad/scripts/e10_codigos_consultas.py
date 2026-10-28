"""E-10 (AUD-40 coerência de códigos; consultas e índices das listagens): SQLite executado.

Parte A: códigos de erro no código-fonte, no OpenAPI (artefato lido) e nos testes.
Parte B: cenários de erro reais (TestClient) comparados às respostas documentadas no OpenAPI da mesma operação.
Parte C: comandos SQL por listagem com 5 e com 25 linhas (N+1) e índices reais após as migrações.
"""
import json
import re
from datetime import date, timedelta
from uuid import uuid4

import yaml
from dad_common import H, ISO, activate, customer, dispatch, draft, setup

setup("e10.db")
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event, inspect  # noqa: E402

from archcorp.infrastructure.db import engine  # noqa: E402
from archcorp.main import app  # noqa: E402


def normaliza(valor):
    if isinstance(valor, dict):
        return {k: normaliza(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [normaliza(v) for v in valor]
    return valor.isoformat() if isinstance(valor, date) else valor


oa = normaliza(yaml.safe_load((ISO / "docs/api/openapi.yaml").read_text(encoding="utf-8")))

# ---------- Parte A: códigos ----------
src = "\n".join(p.read_text(encoding="utf-8") for p in (ISO / "src/archcorp").rglob("*.py"))
errors_py = (ISO / "src/archcorp/errors.py").read_text(encoding="utf-8")
codigos_src = set(re.findall(r'code\s*=\s*"([A-Z_]+)"', src)) | set(re.findall(r'\("([A-Z_]+)", "', errors_py))
codigos_oa = set(re.findall(r'"code": "([A-Z_]+)"', json.dumps(oa)))
tests_txt = "\n".join(p.read_text(encoding="utf-8") for p in (ISO / "tests").glob("test_*.py"))
codigos_test = set(re.findall(r'"code"\]\s*==\s*"([A-Z_]+)"', tests_txt)) | set(re.findall(r'\bcode\s*==\s*"([A-Z_]+)"', tests_txt))
print("== A: códigos de erro (código | OpenAPI | testes)")
for codigo in sorted(codigos_src | codigos_oa | codigos_test):
    print(f"  {codigo:28s} {str(codigo in codigos_src):6s} {str(codigo in codigos_oa):6s} {str(codigo in codigos_test)}")
print("  só no código:", sorted(codigos_src - codigos_oa), "| só no OpenAPI:", sorted(codigos_oa - codigos_src))


def documentado(metodo, modelo):
    op = oa["paths"][modelo][metodo]
    return sorted(op.get("responses", {}).keys()), json.dumps(op)


def observa(rotulo, metodo, modelo, r):
    try:
        corpo = r.json()
    except ValueError:
        corpo = {}
    codigo = corpo.get("code") if isinstance(corpo, dict) else None
    status_doc, texto_op = documentado(metodo, modelo)
    no_oa = (f'"{codigo}"' in texto_op) if codigo else None
    print(f"  {rotulo}: observado={r.status_code} code={codigo} | status documentados={status_doc} "
          f"| code no OpenAPI da operação={no_oa}")


# ---------- Parte B: cenários reais ----------
with TestClient(app, raise_server_exceptions=False) as c:
    print("== B: cenários de erro reais x OpenAPI da mesma operação")
    cust = customer(c, "err")
    ghost = str(uuid4())
    observa("B1 rascunho com cliente inexistente", "post", "/api/v1/contracts/drafts",
            c.post("/api/v1/contracts/drafts", headers={**H, "Idempotency-Key": "E10-1"}, json={
                "customerId": ghost, "serviceCode": "RENTAL-FLEX", "startsOn": "2027-03-01",
                "billing": {"amount": 100, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8}))
    observa("B2 reserva com cliente inexistente", "post", "/api/v1/contracts/reservations",
            c.post("/api/v1/contracts/reservations", headers=H, json={
                "customerId": ghost, "vehicleGroup": "SUV", "protectionCode": "BASICA", "serviceCode": "RENTAL-FLEX",
                "startsOn": "2027-03-01", "endsOn": "2027-03-03", "amount": 100, "currency": "BRL",
                "billingCycle": "ONCE", "slaHours": 8}))
    cid = draft(c, cust, "E10-D").json()["contractId"]
    activate(c, cid, "E10-A")
    dispatch(c)
    tid = c.post("/api/v1/support/tickets", headers={**H, "Idempotency-Key": "E10-T"}, json={
        "customerId": cust["customerId"], "contractId": cid, "serviceCode": "RENTAL-FLEX",
        "category": "OUTAGE", "description": "Chamado de erro"}).json()["ticketId"]
    observa("B3 reconciliar chamado já OPEN", "post", "/api/v1/support/tickets/{ticket_id}/reconcile",
            c.post(f"/api/v1/support/tickets/{tid}/reconcile", headers=H))
    c.post(f"/api/v1/support/tickets/{tid}/resolve", headers=H)
    observa("B4 resolver chamado já resolvido", "post", "/api/v1/support/tickets/{ticket_id}/resolve",
            c.post(f"/api/v1/support/tickets/{tid}/resolve", headers=H))
    inv = c.get("/api/v1/finance/invoices", headers=H, params={"contractId": cid}).json()[0]["invoiceId"]
    observa("B5 pagamento em moeda diferente", "post", "/api/v1/finance/invoices/{invoice_id}/payments",
            c.post(f"/api/v1/finance/invoices/{inv}/payments", headers={**H, "Idempotency-Key": "E10-P5"},
                   json={"amount": 10, "currency": "USD", "reference": "E10-REF-5"}))
    observa("B6 pagamento acima do saldo", "post", "/api/v1/finance/invoices/{invoice_id}/payments",
            c.post(f"/api/v1/finance/invoices/{inv}/payments", headers={**H, "Idempotency-Key": "E10-P6"},
                   json={"amount": 999999, "currency": "BRL", "reference": "E10-REF-6"}))
    observa("B7 CRM com e-mail já cadastrado", "post", "/api/v1/crm/customers",
            c.post("/api/v1/crm/customers", headers=H, json={"name": "Duplicado", "email": cust["email"]}))
    cdraft = draft(c, customer(c, "rasc"), "E10-DR").json()["contractId"]
    observa("B8 encerrar contrato em rascunho", "post", "/api/v1/contracts/{contract_id}/close",
            c.post(f"/api/v1/contracts/{cdraft}/close", headers=H))
    observa("B9 identificador legado inexistente", "get", "/api/v1/integration/legacy-ids/{source_system}/{legacy_id}",
            c.get("/api/v1/integration/legacy-ids/CRM/nao-existe", headers=H))
    c.post("/api/v1/contracts/reservations", headers={**H, "Idempotency-Key": "E10-RK"}, json={
        "customerId": cust["customerId"], "vehicleGroup": "SUV", "protectionCode": "BASICA", "serviceCode": "RENTAL-FLEX",
        "startsOn": "2027-04-01", "endsOn": "2027-04-03", "amount": 100, "currency": "BRL", "billingCycle": "ONCE", "slaHours": 8})
    observa("B10 chave reutilizada em outra reserva", "post", "/api/v1/contracts/reservations",
            c.post("/api/v1/contracts/reservations", headers={**H, "Idempotency-Key": "E10-RK"}, json={
                "customerId": cust["customerId"], "vehicleGroup": "SUV", "protectionCode": "BASICA", "serviceCode": "RENTAL-FLEX",
                "startsOn": "2027-05-01", "endsOn": "2027-05-03", "amount": 100, "currency": "BRL", "billingCycle": "ONCE", "slaHours": 8}))
    observa("B11 tarefa em processo inexistente", "post", "/api/v1/workflow/tasks",
            c.post("/api/v1/workflow/tasks", headers=H, json={"processId": ghost, "title": "Tarefa sintética"}))

    # ---------- Parte C: N+1 e índices ----------
    print("== C: comandos SQL por listagem (N+1)")
    contador = {"n": 0}

    @event.listens_for(engine, "before_cursor_execute")
    def conta(conn, cursor, statement, parameters, context, executemany):
        contador["n"] += 1

    ativos = []

    def novo_contrato(i):
        cu = customer(c, f"lote{i}")
        cid_i = draft(c, cu, f"E10-LD-{i}", starts="2027-01-01").json()["contractId"]
        activate(c, cid_i, f"E10-LA-{i}")
        ativos.append((cu, cid_i))

    def chamados_do_lote(desde):
        for cu, cid_i in ativos[desde:]:
            c.post("/api/v1/support/tickets", headers={**H, "Idempotency-Key": f"E10-LT-{cid_i}"}, json={
                "customerId": cu["customerId"], "contractId": cid_i, "serviceCode": "RENTAL-FLEX",
                "category": "OUTAGE", "description": "Chamado de lote"})

    def medir(rotulo, caminho):
        contador["n"] = 0
        r = c.get(caminho, headers=H)
        print(f"  {rotulo}: http={r.status_code} linhas={len(r.json())} comandos_sql={contador['n']}")

    for i in range(5):
        novo_contrato(i)
    dispatch(c)
    chamados_do_lote(0)
    medir("N=5 GET /finance/invoices", "/api/v1/finance/invoices")
    medir("N=5 GET /support/tickets", "/api/v1/support/tickets")
    for i in range(5, 25):
        novo_contrato(i)
    dispatch(c)
    chamados_do_lote(5)
    medir("N=25 GET /finance/invoices", "/api/v1/finance/invoices")
    medir("N=25 GET /support/tickets", "/api/v1/support/tickets")

    print("== C: índices reais (após as migrações)")
    insp = inspect(engine)
    for tabela in ["crm_customers", "contracts_contracts", "contracts_reservations", "finance_invoices",
                   "finance_payments", "support_tickets", "workflow_instances", "integration_outbox", "integration_inbox"]:
        indices = [(i["name"], i["column_names"]) for i in insp.get_indexes(tabela)]
        unicos = [(u["name"], u["column_names"]) for u in insp.get_unique_constraints(tabela)]
        print(f"  {tabela}: indices={indices} unicos={unicos}")
