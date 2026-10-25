from harness import *
import threading
from sqlalchemy import select, func
from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import OutboxEvent, AuditLog
from archcorp.contracts.models import Contract
import archcorp.contracts.service as cs
from archcorp.main import contracts as svc
with client() as c:
    print("=== Atomicidade: falha apos enqueue e antes do commit na ativacao ===")
    cust = customer(c); d = draft(c, cust, "TX").json()
    orig_audit = cs.audit
    def boom(*a, **k):
        if a[3] == "activate_contract": raise RuntimeError("falha simulada antes do commit")
        return orig_audit(*a, **k)
    cs.audit = boom
    show("ativar com falha injetada", activate(c, d["contractId"], "TX-A"))
    cs.audit = orig_audit
    with SessionLocal() as s:
        print("  status contrato:", s.get(Contract, d["contractId"]).status, "| eventos outbox:", s.scalar(select(func.count()).select_from(OutboxEvent)))
    print("=== Corrida: duas ativacoes concorrentes com chaves diferentes ===")
    d2 = draft(c, cust, "RC", starts="2032-03-03").json()
    barrier = threading.Barrier(2, timeout=10)
    orig_elig = svc.eligible_customer
    def elig(session, cid):
        r = orig_elig(session, cid); barrier.wait(); return r
    svc.eligible_customer = elig
    out = []
    def run(key):
        with SessionLocal() as s:
            try: out.append((key, "ok", svc.activate(s, d2["contractId"], key, CID)[0]["eventId"]))
            except Exception as e: out.append((key, "erro", type(e).__name__ + ": " + str(e)[:120]))
    ts = [threading.Thread(target=run, args=(k,)) for k in ("RC-1", "RC-2")]
    [t.start() for t in ts]; [t.join() for t in ts]
    svc.eligible_customer = orig_elig
    print("  resultados:", out)
    with SessionLocal() as s:
        print("  ContractActivated.v1 para o contrato:", s.scalar(select(func.count()).select_from(OutboxEvent).where(OutboxEvent.event_type == "ContractActivated.v1", OutboxEvent.payload["contractId"].as_string() == d2["contractId"])))
    show("dispatch", dispatch(c))
    show("faturas", c.get("/api/v1/finance/invoices", headers=H))
