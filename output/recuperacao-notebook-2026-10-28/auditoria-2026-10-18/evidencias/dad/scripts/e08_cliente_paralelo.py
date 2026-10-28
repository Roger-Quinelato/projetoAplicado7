"""E-08 (AUD-48, AUD-10 e AUD-11 por HTTP, pagamentos e resolução simultâneos): cliente de requisições paralelas.

Não importa a aplicação. Espera um uvicorn já em execução em BASE (porta 18102), iniciado pelo PowerShell da
execução registrada, e lê o banco pelo DB_URL. Execução registrada: SQLite. PostgreSQL (NÃO executado): subir o
uvicorn com DATABASE_URL de PG descartável e apontar DB_URL para o mesmo banco; as consultas usam SQL textual
portável apenas para contagens simples.
"""
import os
import threading
import time
import uuid
from datetime import date, timedelta

import httpx
from sqlalchemy import create_engine, text

BASE = "http://127.0.0.1:18102"
H = {"Authorization": "Bearer demo-admin", "X-Correlation-ID": "11111111-1111-4111-8111-111111111111"}
eng = create_engine(os.environ["DB_URL"])


def req(method, path, key=None, **kwargs):
    headers = dict(H)
    if key:
        headers["Idempotency-Key"] = key
    with httpx.Client(base_url=BASE, timeout=60) as cl:
        return cl.request(method, path, headers=headers, **kwargs)


def espera_servidor():
    for _ in range(120):
        try:
            if httpx.get(BASE + "/health/live", timeout=2).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise SystemExit("servidor não respondeu em 60 s")


def paralelo(fns):
    barreira = threading.Barrier(len(fns), timeout=30)
    out = [None] * len(fns)

    def run(i):
        try:
            barreira.wait()
            r = fns[i]()
            out[i] = (r.status_code, r.headers.get("Idempotency-Replayed"), r.text[:70] if r.status_code >= 400 else "")
        except Exception as exc:  # registra a falha do cliente
            out[i] = ("EXC", type(exc).__name__, str(exc)[:70])

    ts = [threading.Thread(target=run, args=(i,)) for i in range(len(fns))]
    for t in ts:
        t.start()
    for t in ts:
        t.join(120)
    return out


def q(sql, **params):
    with eng.connect() as conn:
        return [tuple(r) for r in conn.execute(text(sql), params).all()]


def cliente(tag):
    return req("POST", "/api/v1/crm/customers",
               json={"name": "Empresa Sintética", "email": f"{tag}-{uuid.uuid4().hex[:8]}@example.com"}).json()


def rascunho(cust, key, starts, amount=2500):
    return req("POST", "/api/v1/contracts/drafts", key=key, json={
        "customerId": cust["customerId"], "serviceCode": "RENTAL-FLEX", "startsOn": starts,
        "billing": {"amount": amount, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8})


def ticket(cid, cust, key, desc):
    return req("POST", "/api/v1/support/tickets", key=key, json={
        "customerId": cust["customerId"], "contractId": cid, "serviceCode": "RENTAL-FLEX",
        "category": "OUTAGE", "description": desc})


espera_servidor()
cust = cliente("paralelo")
ca = rascunho(cust, "E08-D-A", "2027-09-01").json()["contractId"]
req("POST", f"/api/v1/contracts/{ca}/activate", key="E08-A-A")
req("POST", "/api/v1/integration/outbox/dispatch")
inv_a = req("GET", "/api/v1/finance/invoices", params={"contractId": ca}).json()[0]["invoiceId"]
tk = ticket(ca, cust, "E08-T-BASE", "Chamado base paralelo").json()["ticketId"]

print("S1 reserva com a MESMA Idempotency-Key, 3 requisições simultâneas:")
rbody = {"customerId": cust["customerId"], "vehicleGroup": "SUV", "protectionCode": "BASICA",
         "serviceCode": "RENTAL-FLEX", "startsOn": "2027-10-01", "endsOn": "2027-10-03",
         "amount": 300, "currency": "BRL", "billingCycle": "ONCE", "slaHours": 8}
print("  respostas", paralelo([lambda: req("POST", "/api/v1/contracts/reservations", key="E08-RSV-K1", json=rbody)] * 3))
print("  reservas gravadas", q("SELECT count(*) FROM contracts_reservations WHERE customer_id = :c AND starts_on = '2027-10-01'",
                               c=cust["customerId"]))

print("S2 reserva SEM chave, 3 requisições simultâneas com o mesmo corpo:")
rbody2 = {**rbody, "startsOn": "2027-11-01", "endsOn": "2027-11-03"}
print("  respostas", paralelo([lambda: req("POST", "/api/v1/contracts/reservations", json=rbody2)] * 3))
print("  reservas gravadas", q("SELECT count(*) FROM contracts_reservations WHERE customer_id = :c AND starts_on = '2027-11-01'",
                               c=cust["customerId"]))

print("S3 chamado com a MESMA Idempotency-Key, 2 requisições simultâneas:")
print("  respostas", paralelo([lambda: ticket(ca, cust, "E08-T-SAME", "Chamado paralelo com chave")] * 2))
print("  chamados gravados", q("SELECT count(*) FROM support_tickets WHERE description = 'Chamado paralelo com chave'"))

print("S4 ativação com a MESMA chave, 2 requisições simultâneas:")
cb = rascunho(cust, "E08-D-B", "2027-12-01").json()["contractId"]
print("  respostas", paralelo([lambda: req("POST", f"/api/v1/contracts/{cb}/activate", key="E08-A-SAME")] * 2))
print("  ContractActivated.v1 =", q("SELECT count(*) FROM integration_outbox WHERE event_type = 'ContractActivated.v1' AND payload LIKE :p",
                                   p=f"%{cb}%"))

print("S5 ativação com CHAVES DIFERENTES, 2 requisições simultâneas:")
cc = rascunho(cust, "E08-D-C", "2028-01-01").json()["contractId"]
print("  respostas", paralelo([lambda: req("POST", f"/api/v1/contracts/{cc}/activate", key="E08-A-X1"),
                               lambda: req("POST", f"/api/v1/contracts/{cc}/activate", key="E08-A-X2")]))
print("  ContractActivated.v1 =", q("SELECT count(*) FROM integration_outbox WHERE event_type = 'ContractActivated.v1' AND payload LIKE :p",
                                   p=f"%{cc}%"))

print("S6 resolução SEM chave do mesmo chamado, 2 requisições simultâneas:")
print("  respostas", paralelo([lambda: req("POST", f"/api/v1/support/tickets/{tk}/resolve")] * 2))
print("  TicketResolved.v1 =", q("SELECT count(*) FROM integration_outbox WHERE event_type = 'TicketResolved.v1' AND payload LIKE :p",
                               p=f"%{tk}%"))

print("S7 dois despachos simultâneos com eventos pendentes:")
cd = rascunho(cust, "E08-D-D", "2028-02-01").json()["contractId"]
req("POST", f"/api/v1/contracts/{cd}/activate", key="E08-A-D")
print("  respostas", paralelo([lambda: req("POST", "/api/v1/integration/outbox/dispatch")] * 2))
print("  faturas duplicadas por contrato", q("SELECT contract_id, count(*) FROM finance_invoices GROUP BY contract_id HAVING count(*) > 1"))
print("  inbox duplicada", q("SELECT event_id, consumer, count(*) FROM integration_inbox GROUP BY event_id, consumer HAVING count(*) > 1"))
print("  status da outbox", q("SELECT status, count(*), max(attempts) FROM integration_outbox GROUP BY status"))

print("S8 pagamentos simultâneos 1600 + 1600 sobre fatura de 2500 (referências diferentes):")
pbody = lambda ref: {"amount": 1600, "currency": "BRL", "reference": ref}  # noqa: E731
print("  respostas", paralelo([
    lambda: req("POST", f"/api/v1/finance/invoices/{inv_a}/payments", key="E08-P1", json=pbody("E08-REF-1")),
    lambda: req("POST", f"/api/v1/finance/invoices/{inv_a}/payments", key="E08-P2", json=pbody("E08-REF-2"))]))
print("  soma gravada", q("SELECT sum(amount) FROM finance_payments WHERE invoice_id = :i", i=inv_a),
      "| status", req("GET", f"/api/v1/finance/invoices/{inv_a}").json()["status"])

print("S9 pagamentos simultâneos com a MESMA referência e chaves diferentes (100 + 100):")
print("  respostas", paralelo([
    lambda: req("POST", f"/api/v1/finance/invoices/{inv_a}/payments", key="E08-P3", json={"amount": 100, "currency": "BRL", "reference": "E08-REF-SAME"}),
    lambda: req("POST", f"/api/v1/finance/invoices/{inv_a}/payments", key="E08-P4", json={"amount": 100, "currency": "BRL", "reference": "E08-REF-SAME"})]))
print("  pagamentos com a referência =", q("SELECT count(*) FROM finance_payments WHERE reference = 'E08-REF-SAME'"))

print("S10 contagens finais: contratos ativos", q("SELECT count(*) FROM contracts_contracts WHERE status = 'ACTIVE'"))
