import os, threading, traceback, uuid
os.environ["DATABASE_URL"]="postgresql+psycopg://pgadmin@127.0.0.1:55432/conc2"
from fastapi.testclient import TestClient
from archcorp.main import app, dispatcher
from archcorp.infrastructure.db import SessionLocal
H={"Authorization":"Bearer demo-admin"}
with TestClient(app) as c:
    cid=c.post("/api/v1/crm/customers",headers=H,json={"name":"Inproc","email":f"i{uuid.uuid4().hex[:8]}@example.com"}).json()["customerId"]
    k=c.post("/api/v1/contracts/drafts",headers={**H,"Idempotency-Key":"x1"},json={"customerId":cid,"serviceCode":"RENTAL-FLEX","startsOn":"2027-05-01","billing":{"amount":10,"currency":"BRL","cycle":"MONTHLY"}}).json()["contractId"]
    c.post(f"/api/v1/contracts/{k}/activate",headers={**H,"Idempotency-Key":"a1"})
b=threading.Barrier(2); res=[]
def run():
    with SessionLocal() as s:
        b.wait()
        try: res.append(("ok",dispatcher.dispatch_pending(s)))
        except Exception as e: res.append(("exc",type(e).__module__+"."+type(e).__name__, str(e).splitlines()[0][:200]))
ts=[threading.Thread(target=run) for _ in range(2)]; [t.start() for t in ts]; [t.join() for t in ts]
for r in res: print(r)
with SessionLocal() as s:
    from sqlalchemy import text
    print(s.execute(text("select status,attempts,left(coalesce(last_error,''),120) from integration_outbox")).all())
