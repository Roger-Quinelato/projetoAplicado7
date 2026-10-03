"""Experimento de concorrência real (Agente 3) contra a API em execução (PostgreSQL descartável).
Uso: python conc_exp.py <base_url> <pg_dsn_psycopg> <rodadas>"""
import sys
import threading
import uuid
from collections import Counter

import httpx
import psycopg

BASE, DSN, ROUNDS = sys.argv[1], sys.argv[2], int(sys.argv[3])
ADMIN = {"Authorization": "Bearer demo-admin"}
c = httpx.Client(base_url=BASE, headers=ADMIN, timeout=60)


def parallel(n, fn):
    barrier = threading.Barrier(n)
    out = [None] * n

    def run(i):
        barrier.wait()
        try:
            out[i] = fn(i)
        except Exception as exc:  # registra exceção de cliente
            out[i] = f"EXC {type(exc).__name__}"
    ts = [threading.Thread(target=run, args=(i,)) for i in range(n)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    return out


def customer():
    r = c.post("/api/v1/crm/customers", json={"name": "Cliente Concorrencia", "email": f"c{uuid.uuid4().hex[:10]}@example.com"})
    r.raise_for_status()
    return r.json()["customerId"]


def draft(cid, day):
    r = c.post("/api/v1/contracts/drafts", headers={"Idempotency-Key": str(uuid.uuid4())}, json={
        "customerId": cid, "serviceCode": "RENTAL-FLEX", "startsOn": f"2027-01-{day:02d}",
        "billing": {"amount": 100, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8})
    r.raise_for_status()
    return r.json()["contractId"]


def db(sql, *args):
    with psycopg.connect(DSN) as conn:
        return conn.execute(sql, args).fetchall()


summary = Counter()
print(f"== base={BASE} rodadas={ROUNDS}")
for rnd in range(ROUNDS):
    cid = customer()
    # A) duas ativações simultâneas com chaves DIFERENTES (ex.: duplo clique no frontend, que gera chave nova por clique)
    k = draft(cid, 1 + rnd % 28)
    codes = parallel(2, lambda i: c.post(f"/api/v1/contracts/{k}/activate", headers={"Idempotency-Key": str(uuid.uuid4())}).status_code)
    ev = db("SELECT count(*) FROM integration_outbox WHERE event_type='ContractActivated.v1' AND payload->>'contractId'=%s", k)[0][0]
    summary[f"A_ativacao_chaves_diferentes codes={sorted(codes)} eventos={ev}"] += 1
    # B) duas ativações simultâneas com a MESMA chave
    cid2 = customer()
    k2 = draft(cid2, 1 + rnd % 28)
    key = str(uuid.uuid4())
    codes = parallel(2, lambda i: c.post(f"/api/v1/contracts/{k2}/activate", headers={"Idempotency-Key": key}).status_code)
    ev = db("SELECT count(*) FROM integration_outbox WHERE event_type='ContractActivated.v1' AND payload->>'contractId'=%s", k2)[0][0]
    summary[f"B_ativacao_mesma_chave codes={sorted(codes)} eventos={ev}"] += 1
    # C) duas reservas simultâneas com a mesma Idempotency-Key
    rkey = str(uuid.uuid4())
    body = {"customerId": cid, "vehicleGroup": "Economico", "protectionCode": "BASICA", "serviceCode": "RENTAL-FLEX",
            "startsOn": "2027-02-01", "endsOn": "2027-02-05", "amount": 300, "currency": "BRL", "billingCycle": "ONCE", "slaHours": 8}
    codes = parallel(2, lambda i: c.post("/api/v1/contracts/reservations", headers={"Idempotency-Key": rkey}, json=body).status_code)
    n = db("SELECT count(*) FROM contracts_reservations WHERE customer_id=%s AND starts_on='2027-02-01'", cid)[0][0]
    summary[f"C_reserva_mesma_chave codes={sorted(codes)} reservas={n}"] += 1
    # D) duas reservas simultâneas sem chave (cliente que não envia Idempotency-Key)
    codes = parallel(2, lambda i: c.post("/api/v1/contracts/reservations", json={**body, "startsOn": "2027-03-01", "endsOn": "2027-03-02"}).status_code)
    n = db("SELECT count(*) FROM contracts_reservations WHERE customer_id=%s AND starts_on='2027-03-01'", cid)[0][0]
    summary[f"D_reserva_sem_chave codes={sorted(codes)} reservas={n}"] += 1
    # E) dois despachos simultâneos
    codes = parallel(2, lambda i: (lambda r: (r.status_code, r.text[:80]))(c.post("/api/v1/integration/outbox/dispatch")))
    summary[f"E_despacho_paralelo codes={sorted(x[0] if isinstance(x, tuple) else x for x in codes)}"] += 1
    for x in codes:
        if isinstance(x, tuple) and x[0] != 200:
            summary[f"E_corpo_nao200={x[1]}"] += 1
    # Normaliza: despacho final sequencial
    c.post("/api/v1/integration/outbox/dispatch")

dup_inv = db("SELECT contract_id, count(*) FROM finance_invoices GROUP BY contract_id HAVING count(*)>1")
dup_proc = db("SELECT process_type, reference_id, count(*) FROM workflow_instances GROUP BY 1,2 HAVING count(*)>1")
dup_inbox = db("SELECT event_id, consumer, count(*) FROM integration_inbox GROUP BY 1,2 HAVING count(*)>1")
status = db("SELECT status, count(*), max(attempts) FROM integration_outbox GROUP BY status")
active = db("SELECT count(*) FROM contracts_contracts WHERE status='ACTIVE'")[0][0]
inv = db("SELECT count(*) FROM finance_invoices")[0][0]
multi_ev = db("SELECT payload->>'contractId', count(*) FROM integration_outbox WHERE event_type='ContractActivated.v1' GROUP BY 1 HAVING count(*)>1")
for k, v in sorted(summary.items()):
    print(f"  {v:3d}x {k}")
print(f"  contratos_ativos={active} faturas={inv} faturas_duplicadas={len(dup_inv)} processos_duplicados={len(dup_proc)} inbox_duplicado={len(dup_inbox)}")
print(f"  contratos_com_>1_ContractActivated={len(multi_ev)} status_outbox={status}")
