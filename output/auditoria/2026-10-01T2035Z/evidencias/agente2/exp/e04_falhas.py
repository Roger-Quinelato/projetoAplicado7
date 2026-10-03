from harness import *
import time
from sqlalchemy import select, func
from archcorp.config import settings
from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import OutboxEvent, InboxEvent, AuditLog
from archcorp.finance.models import Invoice
from archcorp.workflow.models import ProcessInstance, ProcessTask
def counts(tag):
    with SessionLocal() as s:
        print(f"  <{tag}> invoices={s.scalar(select(func.count()).select_from(Invoice))} processes={s.scalar(select(func.count()).select_from(ProcessInstance))} tasks={s.scalar(select(func.count()).select_from(ProcessTask))} inbox={[ (i.consumer) for i in s.scalars(select(InboxEvent))]} outbox={[ (e.event_type,e.status,e.attempts,(e.last_error or '')[:60]) for e in s.scalars(select(OutboxEvent))]}")
orig = dict(dispatcher.handlers)
with client() as c:
    print("=== Cenario A: falha parcial (finance ok, workflow levanta RuntimeError apos gravar processo) ===")
    cust = customer(c)
    d = draft(c, cust, "PA").json(); activate(c, d["contractId"], "PA-A")
    from archcorp.workflow.service import handle_contract_activated as wf
    def wf_partial(session, env):
        wf(session, env)          # grava processo + tarefa
        raise RuntimeError("falha simulada apos efeito parcial do workflow")
    dispatcher.handlers["ContractActivated.v1"] = [orig["ContractActivated.v1"][0], ("workflow-preparacao-retirada", wf_partial)]
    show("dispatch com falha parcial", dispatch(c)); counts("apos falha parcial")
    dispatcher.handlers["ContractActivated.v1"] = orig["ContractActivated.v1"]
    show("dispatch apos corrigir", dispatch(c)); counts("apos correcao")
    print("=== Cenario B: falha de banco (IntegrityError) dentro de um consumidor ===")
    cust2 = customer(c)
    d2 = draft(c, cust2, "PB").json(); activate(c, d2["contractId"], "PB-A")
    def wf_integrity(session, env):
        session.add(InboxEvent(event_id=env["eventId"], consumer="finance"))  # viola uq_inbox_event_consumer (finance ja registrado)
        session.flush()
    dispatcher.handlers["ContractActivated.v1"] = [orig["ContractActivated.v1"][0], ("workflow-preparacao-retirada", wf_integrity)]
    for i in range(4):
        r = dispatch(c); show(f"dispatch IntegrityError #{i+1}", r)
    counts("apos IntegrityError x4")
    dispatcher.handlers["ContractActivated.v1"] = orig["ContractActivated.v1"]
    show("dispatch apos corrigir B", dispatch(c)); counts("apos correcao B")
    print("=== Cenario C: RabbitMQ configurado e indisponivel (porta fechada) ===")
    cust3 = customer(c)
    d3 = draft(c, cust3, "PC").json(); activate(c, d3["contractId"], "PC-A")
    settings.rabbitmq_url = "amqp://guest:guest@127.0.0.1:5999/%2F"
    for i in range(3):
        t=time.time(); r = dispatch(c); show(f"dispatch broker indisponivel #{i+1} ({time.time()-t:.2f}s)", r)
    counts("apos 3 tentativas com broker indisponivel")
    show("failures", c.get("/api/v1/integration/failures", headers=H))
    # Um novo evento de outro tipo fica bloqueado?
    cust4 = customer(c); c.patch(f"/api/v1/crm/customers/{cust4['customerId']}", headers=H, json={"name": "Nome Novo"})
    r = dispatch(c); show("dispatch CustomerUpdated com broker indisponivel", r); counts("customerupdated com broker down")
    settings.rabbitmq_url = None
    ev = c.get("/api/v1/integration/failures", headers=H).json()
    for f in ev:
        show("reprocess", c.post(f"/api/v1/integration/failures/{f['eventId']}/reprocess", headers=H))
    show("dispatch apos broker volta (sem broker)", dispatch(c)); counts("final C")
    with SessionLocal() as s:
        print("  auditoria reprocess:", [(a.operation, a.result, a.details) for a in s.scalars(select(AuditLog).where(AuditLog.operation=="reprocess_event"))])
