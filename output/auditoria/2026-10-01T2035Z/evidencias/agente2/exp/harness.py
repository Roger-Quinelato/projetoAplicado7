"""Harness de experimentos do Agente 2 (cópia isolada, SQLite descartável)."""
import os, sys, json, pathlib, uuid
from datetime import date, timedelta
SP = pathlib.Path("/tmp/claude-0/-home-user-projetoAplicado7/ec00d59b-c354-5d1f-b4d6-080b88ac1d06/scratchpad")
NAME = os.environ.get("EXP", "x")
DB = SP / "agente2" / "run" / f"{NAME}.db"
if DB.exists() and not os.environ.get("KEEP_DB"):
    DB.unlink()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{DB}")
os.environ.pop("RABBITMQ_URL", None) if not os.environ.get("KEEP_RMQ") else None
sys.path.insert(0, str(SP / "iso" / "src"))
import logging
from fastapi.testclient import TestClient
from archcorp.main import app, dispatcher
logging.disable(logging.CRITICAL)
CID = "11111111-1111-4111-8111-111111111111"
H = {"Authorization": "Bearer demo-admin", "X-Correlation-ID": CID}

def show(label, r):
    try:
        body = r.json()
    except Exception:
        body = r.text
    hdr = {k: v for k, v in r.headers.items() if k.lower() in ("idempotency-replayed",)}
    print(f"[{label}] {r.request.method} {r.request.url.path} -> {r.status_code} {hdr} {json.dumps(body, ensure_ascii=False)[:600]}")
    return body

def customer(c, email=None, **kw):
    email = email or f"c{uuid.uuid4().hex[:8]}@example.com"
    return c.post("/api/v1/crm/customers", headers=H, json={"name": "Empresa Sintética", "email": email, **kw}).json()

def draft(c, cust, key, amount=2500, starts=None, sla=8):
    starts = starts or (date.today() + timedelta(days=3)).isoformat()
    return c.post("/api/v1/contracts/drafts", headers={**H, "Idempotency-Key": key}, json={
        "customerId": cust["customerId"], "serviceCode": "RENTAL-FLEX", "startsOn": starts,
        "billing": {"amount": amount, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": sla})

def activate(c, contract_id, key):
    return c.post(f"/api/v1/contracts/{contract_id}/activate", headers={**H, "Idempotency-Key": key})

def dispatch(c):
    return c.post("/api/v1/integration/outbox/dispatch", headers=H)

def client():
    return TestClient(app)
