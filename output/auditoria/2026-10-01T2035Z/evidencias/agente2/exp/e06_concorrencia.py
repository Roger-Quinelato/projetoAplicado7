from harness import *
import threading
from sqlalchemy import select, func
from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import OutboxEvent, InboxEvent
from archcorp.finance.models import Invoice
from archcorp.workflow.models import ProcessInstance
from archcorp.integration.service import EventDispatcher
orig = dict(dispatcher.handlers)
calls = {"finance": 0, "broker": 0}
barrier = threading.Barrier(2, timeout=10)
fin = orig["ContractActivated.v1"][0][1]
def fin_wrapped(session, env):
    calls["finance"] += 1
    barrier.wait()            # ambos os despachantes passaram pela verificacao da inbox
    fin(session, env)
dispatcher.handlers["ContractActivated.v1"] = [("finance", fin_wrapped), orig["ContractActivated.v1"][1]]
EventDispatcher._publish_broker = staticmethod(lambda env: calls.__setitem__("broker", calls["broker"] + 1))
with client() as c:
    cust = customer(c); d = draft(c, cust, "CC").json(); activate(c, d["contractId"], "CC-A")
    results = []
    def run():
        with SessionLocal() as s:
            try:
                results.append(("ok", dispatcher.dispatch_pending(s)))
            except Exception as exc:
                results.append(("erro", type(exc).__name__ + ": " + str(exc)[:160]))
    ts = [threading.Thread(target=run) for _ in range(2)]
    [t.start() for t in ts]; [t.join() for t in ts]
    print("resultados:", results)
    print("chamadas ao handler finance:", calls["finance"], "| publicacoes broker simuladas:", calls["broker"])
    with SessionLocal() as s:
        print("invoices:", s.scalar(select(func.count()).select_from(Invoice)), "processes:", s.scalar(select(func.count()).select_from(ProcessInstance)),
              "inbox:", [i.consumer for i in s.scalars(select(InboxEvent))], "outbox:", [(e.status, e.attempts) for e in s.scalars(select(OutboxEvent))])
