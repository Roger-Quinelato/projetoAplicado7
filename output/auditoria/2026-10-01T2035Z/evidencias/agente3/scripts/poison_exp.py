import os, uuid, json
os.environ["DATABASE_URL"]="postgresql+psycopg://pgadmin@127.0.0.1:55432/conc2"
from fastapi.testclient import TestClient
from archcorp.main import app
from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import OutboxEvent
from sqlalchemy import text
H={"Authorization":"Bearer demo-admin"}
with TestClient(app, raise_server_exceptions=False) as c:
    # evento "venenoso": payload com valor monetário fora da precisão Numeric(14,2) -> erro de banco no flush do consumidor financeiro
    with SessionLocal() as s:
        s.add(OutboxEvent(event_type="ContractActivated.v1", producer="contracts", correlation_id=str(uuid.uuid4()),
            payload={"contractId": str(uuid.uuid4()), "customerId": str(uuid.uuid4()), "billing": {"amount": "1e20", "currency": "BRL", "cycle":"MONTHLY"}}))
        s.commit()
    # evento legítimo posterior
    cid=c.post("/api/v1/crm/customers",headers=H,json={"name":"Depois","email":f"d{uuid.uuid4().hex[:8]}@example.com"}).json()["customerId"]
    k=c.post("/api/v1/contracts/drafts",headers={**H,"Idempotency-Key":str(uuid.uuid4())},json={"customerId":cid,"serviceCode":"RENTAL-FLEX","startsOn":"2027-06-01","billing":{"amount":10,"currency":"BRL","cycle":"MONTHLY"}}).json()["contractId"]
    c.post(f"/api/v1/contracts/{k}/activate",headers={**H,"Idempotency-Key":str(uuid.uuid4())})
    for i in range(5):
        r=c.post("/api/v1/integration/outbox/dispatch",headers=H)
        print("despacho",i+1,r.status_code,r.text[:90])
    with SessionLocal() as s:
        print(s.execute(text("select event_type,status,attempts,left(coalesce(last_error,''),60) from integration_outbox where status<>'PUBLISHED' order by occurred_at")).all())
        print("fatura do contrato legítimo:", s.execute(text("select count(*) from finance_invoices where contract_id=:k"),{"k":k}).scalar())
    print("falhas listadas:", c.get("/api/v1/integration/failures",headers=H).json())
