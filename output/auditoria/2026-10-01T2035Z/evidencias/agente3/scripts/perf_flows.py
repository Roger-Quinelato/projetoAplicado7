import os, sys, time, statistics, uuid
os.environ["DATABASE_URL"]=sys.argv[1]
from fastapi.testclient import TestClient
from archcorp.infrastructure.db import Base, engine
from archcorp.main import app
Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
H={"Authorization":"Bearer demo-admin"}
f1=[];f2=[];f3=[]
with TestClient(app) as c:
    for i in range(100):
        t=time.perf_counter()
        cid=c.post("/api/v1/crm/customers",headers=H,json={"name":"Perf","email":f"p{i}-{uuid.uuid4().hex[:6]}@example.com"}).json()["customerId"]
        k=c.post("/api/v1/contracts/drafts",headers={**H,"Idempotency-Key":str(uuid.uuid4())},json={"customerId":cid,"serviceCode":"RENTAL-FLEX","startsOn":"2027-01-01","billing":{"amount":10,"currency":"BRL","cycle":"MONTHLY"}}).json()["contractId"]
        f1.append((time.perf_counter()-t)*1000); t=time.perf_counter()
        c.post(f"/api/v1/contracts/{k}/activate",headers={**H,"Idempotency-Key":str(uuid.uuid4())}).raise_for_status()
        c.post("/api/v1/integration/outbox/dispatch",headers=H).raise_for_status()
        f2.append((time.perf_counter()-t)*1000); t=time.perf_counter()
        r=c.post("/api/v1/support/tickets",headers={**H,"Idempotency-Key":str(uuid.uuid4())},json={"customerId":cid,"contractId":k,"serviceCode":"RENTAL-FLEX","category":"OUTAGE","description":"Pneu furado sintetico"}); r.raise_for_status()
        c.post("/api/v1/integration/outbox/dispatch",headers=H).raise_for_status()
        f3.append((time.perf_counter()-t)*1000)
p=lambda s: statistics.quantiles(s,n=100,method="inclusive")[94]
print(f"F1(cliente+rascunho) p95={p(f1):.1f}ms F2(ativar+despachar) p95={p(f2):.1f}ms F3(chamado+despachar) p95={p(f3):.1f}ms n=100")
