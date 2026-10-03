import os, sys, uuid
os.environ["DATABASE_URL"]=sys.argv[1]
from fastapi.testclient import TestClient
from sqlalchemy import text
from archcorp.infrastructure.db import Base, engine, SessionLocal
from archcorp.main import app
Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
H={"Authorization":"Bearer demo-admin"}
with TestClient(app, raise_server_exceptions=False) as c:
    for amt, pay in [("100.10","100.095"), ("100.10","0.004")]:
        cid=c.post("/api/v1/crm/customers",headers=H,json={"name":"Pagador","email":f"p{uuid.uuid4().hex[:6]}@example.com"}).json()["customerId"]
        k=c.post("/api/v1/contracts/drafts",headers={**H,"Idempotency-Key":str(uuid.uuid4())},json={"customerId":cid,"serviceCode":"RENTAL-FLEX","startsOn":"2027-01-01","billing":{"amount":amt,"currency":"BRL","cycle":"MONTHLY"}}).json()["contractId"]
        c.post(f"/api/v1/contracts/{k}/activate",headers={**H,"Idempotency-Key":str(uuid.uuid4())}); c.post("/api/v1/integration/outbox/dispatch",headers=H)
        inv=[i for i in c.get("/api/v1/finance/invoices",headers=H).json() if i["contractId"]==k][0]
        r=c.post(f"/api/v1/finance/invoices/{inv['invoiceId']}/payments",headers=H,json={"amount":pay,"currency":"BRL","reference":f"REF-{uuid.uuid4().hex[:8]}"})
        after=c.get(f"/api/v1/finance/invoices/{inv['invoiceId']}",headers=H).json()
        with SessionLocal() as s:
            row=s.execute(text("select amount from finance_payments where invoice_id=:i"),{"i":inv["invoiceId"]}).all()
        print(f"fatura={amt} pagamento_enviado={pay} -> HTTP {r.status_code} resp={r.text[:160]}")
        print(f"   gravado_no_banco={row} fatura_após={ {k2:after.get(k2) for k2 in ('amount','paidAmount','balance','status')} }")
