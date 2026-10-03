from harness import *
import time
from sqlalchemy import select
from archcorp.config import settings
from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import OutboxEvent, InboxEvent
orig = dict(dispatcher.handlers)
def outbox():
    with SessionLocal() as s:
        return [(e.event_type, e.status, e.attempts) for e in s.scalars(select(OutboxEvent).order_by(OutboxEvent.occurred_at))]
with client() as c:
    print("=== B2: evento envenenado (erro de banco no consumidor) bloqueia eventos posteriores ===")
    cust = customer(c); d = draft(c, cust, "B2").json(); activate(c, d["contractId"], "B2-A")
    def wf_integrity(session, env):
        session.add(InboxEvent(event_id=env["eventId"], consumer="finance")); session.flush()
    dispatcher.handlers["ContractActivated.v1"] = [orig["ContractActivated.v1"][0], ("workflow-preparacao-retirada", wf_integrity)]
    # eventos posteriores, de outro tipo
    c.patch(f"/api/v1/crm/customers/{cust['customerId']}", headers=H, json={"name": "Nome Posterior"})
    for i in range(3):
        show(f"dispatch #{i+1}", dispatch(c)); print("   outbox:", outbox())
    show("failures (vazio?)", c.get("/api/v1/integration/failures", headers=H))
    dispatcher.handlers["ContractActivated.v1"] = orig["ContractActivated.v1"]
    print("=== C2: broker em host sem resposta (blackhole) - tempo de um despacho ===")
    cust2 = customer(c); d2 = draft(c, cust2, "C2").json(); activate(c, d2["contractId"], "C2-A")
    settings.rabbitmq_url = "amqp://guest:guest@10.255.255.1:5672/%2F"
    t = time.time(); r = dispatch(c); show(f"dispatch blackhole ({time.time()-t:.1f}s)", r)
    with SessionLocal() as s:
        print("   last_error:", repr([e.last_error for e in s.scalars(select(OutboxEvent).where(OutboxEvent.attempts>0))]))
    settings.rabbitmq_url = None
