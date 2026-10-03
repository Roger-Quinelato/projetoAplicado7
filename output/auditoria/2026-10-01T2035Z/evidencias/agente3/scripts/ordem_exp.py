"""Revisão independente de A2-03 (Agente 3). Dois caminhos:
 (1) falha transitória de BANCO real (lock_timeout com linha bloqueada) na projeção v1;
 (2) falha transitória NÃO-banco (exceção Python injetada por janela de tempo) na projeção v1."""
import os, sys, uuid, threading
os.environ["DATABASE_URL"] = sys.argv[1]
import psycopg
from fastapi.testclient import TestClient
from sqlalchemy import text
from archcorp.infrastructure.db import Base, engine, SessionLocal
import archcorp.main as m
from archcorp.config import settings
DSN = sys.argv[2]
H = {"Authorization": "Bearer demo-admin"}
Base.metadata.drop_all(engine); Base.metadata.create_all(engine)

def setup(c):
    cid = c.post("/api/v1/crm/customers", headers=H, json={"name": "Nome Original", "email": f"o{uuid.uuid4().hex[:6]}@example.com"}).json()["customerId"]
    k = c.post("/api/v1/contracts/drafts", headers={**H, "Idempotency-Key": str(uuid.uuid4())}, json={"customerId": cid, "serviceCode": "RENTAL-FLEX", "startsOn": "2027-01-01", "billing": {"amount": 10, "currency": "BRL", "cycle": "MONTHLY"}}).json()["contractId"]
    return cid, k

def proj(k):
    with SessionLocal() as s:
        return s.execute(text("select customer_name from contracts_contracts where contract_id=:k"), {"k": k}).scalar()

def outbox():
    with SessionLocal() as s:
        return s.execute(text("select payload->>'name', status, attempts, coalesce(last_error,'') from integration_outbox where event_type='CustomerUpdated.v1' order by occurred_at")).all()

with TestClient(m.app, raise_server_exceptions=False) as c:
    print("== Caminho 1: falha transitória de banco real (lock_timeout) ==")
    cid, k = setup(c)
    c.patch(f"/api/v1/crm/customers/{cid}", headers=H, json={"name": "Nome Versao 1"})
    locker = psycopg.connect(DSN); locker.execute("BEGIN"); locker.execute("SELECT 1 FROM contracts_contracts WHERE contract_id=%s FOR UPDATE", (k,))
    for i in range(3):
        r = c.post("/api/v1/integration/outbox/dispatch", headers=H); print(f"  despacho {i+1}: {r.status_code} {r.text[:60]}  outbox={outbox()}")
    locker.rollback(); locker.close()
    r = c.post("/api/v1/integration/outbox/dispatch", headers=H); print(f"  após liberar lock: {r.status_code} {r.json()} projeção={proj(k)!r} outbox={outbox()}")

    print("== Caminho 2: falha transitória não-banco (exceção Python) ==")
    with SessionLocal() as s:
        s.execute(text("delete from integration_outbox")); s.commit()
    cid, k = setup(c)
    c.patch(f"/api/v1/crm/customers/{cid}", headers=H, json={"name": "Nome Versao 1"})
    original = m.dispatcher.handlers["CustomerUpdated.v1"]
    falhar = {"on": True}
    def projecao_instavel(session, env):
        if falhar["on"]:
            raise ConnectionError("Contracts indisponível (simulado)")
        return original[0][1](session, env)
    m.dispatcher.handlers["CustomerUpdated.v1"] = [(original[0][0], projecao_instavel)]
    for i in range(settings.retry_limit):
        c.post("/api/v1/integration/outbox/dispatch", headers=H)
    print(f"  após {settings.retry_limit} despachos: outbox={outbox()} projeção={proj(k)!r}")
    falhar["on"] = False
    c.patch(f"/api/v1/crm/customers/{cid}", headers=H, json={"name": "Nome Versao 2"})
    print(f"  despacho v2: {c.post('/api/v1/integration/outbox/dispatch', headers=H).json()} projeção={proj(k)!r}")
    fid = c.get("/api/v1/integration/failures", headers=H).json()[0]["eventId"]
    print(f"  reprocess v1: {c.post(f'/api/v1/integration/failures/{fid}/reprocess', headers=H).status_code}; despacho: {c.post('/api/v1/integration/outbox/dispatch', headers=H).json()}")
    crm = c.get(f"/api/v1/crm/customers/{cid}", headers=H).json()["name"]
    print(f"  RESULTADO: CRM (fonte oficial)={crm!r}  projeção Contracts={proj(k)!r}  outbox={outbox()}")
    m.dispatcher.handlers["CustomerUpdated.v1"] = original
