from harness import *
from sqlalchemy import select, func, text
from archcorp.infrastructure.db import SessionLocal, engine
from archcorp.integration.models import OutboxEvent, InboxEvent
from archcorp.finance.models import Invoice
from archcorp.workflow.models import ProcessInstance, ProcessTask
def counts(tag):
    with SessionLocal() as s:
        print(f"  <{tag}> invoices={s.scalar(select(func.count()).select_from(Invoice))} processes={s.scalar(select(func.count()).select_from(ProcessInstance))} tasks={s.scalar(select(func.count()).select_from(ProcessTask))} inbox={s.scalar(select(func.count()).select_from(InboxEvent))} outbox={[ (e.event_type,e.status,e.attempts) for e in s.scalars(select(OutboxEvent))]}")
with client() as c:
    cust = customer(c)
    d = draft(c, cust, "D1", amount=100.10).json()
    a1 = show("ativar A1", activate(c, d["contractId"], "A1"))
    show("ativar A1 de novo", activate(c, d["contractId"], "A1"))
    show("ativar A2 (outra chave)", activate(c, d["contractId"], "A2"))
    show("ativar sem chave", c.post(f"/api/v1/contracts/{d['contractId']}/activate", headers=H))
    show("ativar contrato inexistente", activate(c, "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "A3"))
    # mesma chave A1 em outro contrato
    d2 = draft(c, cust, "D2", amount=10, starts="2030-01-01").json()
    show("mesma chave A1 em OUTRO contrato", activate(c, d2["contractId"], "A1"))
    counts("antes do despacho")
    show("dispatch 1", dispatch(c)); counts("apos dispatch 1")
    show("dispatch 2", dispatch(c)); counts("apos dispatch 2")
    # reentrega: recoloca o evento em PENDING (simula reentrega/reprocessamento)
    with SessionLocal() as s:
        ev = s.get(OutboxEvent, a1["eventId"]); ev.status = "PENDING"; s.commit()
    show("dispatch 3 (reentrega simulada do mesmo eventId)", dispatch(c)); counts("apos reentrega")
    # reentrega com inbox apagada (simula consumidor sem inbox / perda) -> restricoes de negocio
    with SessionLocal() as s:
        s.execute(text("DELETE FROM integration_inbox")); ev = s.get(OutboxEvent, a1["eventId"]); ev.status = "PENDING"; s.commit()
    show("dispatch 4 (reentrega sem inbox)", dispatch(c)); counts("apos reentrega sem inbox")
    # fatura
    inv = show("faturas", c.get("/api/v1/finance/invoices", headers=H))
    with engine.connect() as conn:
        print("  tipo coluna amount no SQLite:", conn.execute(text("select typeof(amount), amount from finance_invoices")).all())
    with SessionLocal() as s:
        print("  payload do evento billing:", s.get(OutboxEvent, a1["eventId"]).payload["billing"])
