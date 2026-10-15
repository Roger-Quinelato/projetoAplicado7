import os, sys, time, uuid
os.environ["DATABASE_URL"]=sys.argv[1]; os.environ["RABBITMQ_URL"]=sys.argv[2]
from fastapi.testclient import TestClient
from archcorp.main import app
from archcorp.infrastructure.db import Base, engine, SessionLocal
from sqlalchemy import text
Base.metadata.drop_all(engine)
H={"Authorization":"Bearer demo-admin"}
with TestClient(app) as c:
    cid=c.post("/api/v1/crm/customers",headers=H,json={"name":"Rabbit","email":"r@example.com"}).json()["customerId"]
    k=c.post("/api/v1/contracts/drafts",headers={**H,"Idempotency-Key":"r1"},json={"customerId":cid,"serviceCode":"RENTAL-FLEX","startsOn":"2027-01-01","billing":{"amount":10,"currency":"BRL","cycle":"MONTHLY"}}).json()["contractId"]
    c.post(f"/api/v1/contracts/{k}/activate",headers={**H,"Idempotency-Key":"a1"})
    for i in range(4):
        t=time.perf_counter(); r=c.post("/api/v1/integration/outbox/dispatch",headers=H); d=time.perf_counter()-t
        with SessionLocal() as s:
            row=s.execute(text("select status,attempts,substr(coalesce(last_error,''),1,90) from integration_outbox where event_type='ContractActivated.v1'")).one()
            inv=s.execute(text("select count(*) from finance_invoices")).scalar(); pr=s.execute(text("select count(*) from workflow_instances")).scalar()
        print(f"despacho {i+1}: http={r.status_code} corpo={r.json()} dur={d:.2f}s evento={tuple(row)} faturas={inv} processos={pr}")
    print("falhas:", [ (f['eventType'],f['attempts'],f['reason'][:60]) for f in c.get("/api/v1/integration/failures",headers=H).json()])
    ev=c.get("/api/v1/integration/failures",headers=H).json()
    if ev:
        r=c.post(f"/api/v1/integration/failures/{ev[0]['eventId']}/reprocess",headers=H); print("reprocess:",r.status_code,r.json())
        r=c.post("/api/v1/integration/outbox/dispatch",headers=H); print("despacho após reprocess:", r.json())
        with SessionLocal() as s:
            print("faturas após reprocess:", s.execute(text("select count(*) from finance_invoices")).scalar())
