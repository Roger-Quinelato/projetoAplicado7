from harness import *
import yaml
from sqlalchemy import select
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import OutboxEvent
from archcorp.contracts.models import Contract
from archcorp.config import settings
orig = dict(dispatcher.handlers)
with client() as c:
    print("=== Reprocessamento de CustomerUpdated.v1 antigo sobrescreve projecao mais nova ===")
    cust = customer(c); d = draft(c, cust, "O1").json()
    c.patch(f"/api/v1/crm/customers/{cust['customerId']}", headers=H, json={"name": "Nome Versao 1"})
    proj = orig["CustomerUpdated.v1"][0][1]
    state = {"fail": True}
    def flaky(session, env):
        if env["payload"]["name"] == "Nome Versao 1" and state["fail"]:
            raise RuntimeError("falha transitoria simulada")
        proj(session, env)
    dispatcher.handlers["CustomerUpdated.v1"] = [("contracts-customer-projection", flaky)]
    for i in range(settings.retry_limit):
        dispatch(c)
    c.patch(f"/api/v1/crm/customers/{cust['customerId']}", headers=H, json={"name": "Nome Versao 2"})
    show("dispatch v2", dispatch(c))
    with SessionLocal() as s:
        print("  projecao apos v2:", s.get(Contract, d["contractId"]).customer_name)
    state["fail"] = False
    f = c.get("/api/v1/integration/failures", headers=H).json(); show("failures", c.get("/api/v1/integration/failures", headers=H))
    c.post(f"/api/v1/integration/failures/{f[0]['eventId']}/reprocess", headers=H)
    show("dispatch reprocessado v1", dispatch(c))
    with SessionLocal() as s:
        print("  projecao em contracts apos reprocessar v1:", s.get(Contract, d["contractId"]).customer_name)
    show("CRM (fonte oficial)", c.get(f"/api/v1/crm/customers/{cust['customerId']}", headers=H))
    dispatcher.handlers["CustomerUpdated.v1"] = orig["CustomerUpdated.v1"]
    print("=== Envelopes reais x AsyncAPI (amount 100.10, dueAt) com FormatChecker ===")
    d2 = draft(c, cust, "O2", amount=100.10, starts="2031-02-02").json(); a = activate(c, d2["contractId"], "O2-A").json()
    t = c.post("/api/v1/support/tickets", headers={**H, "Idempotency-Key": "O-T"}, json={"customerId": cust["customerId"], "contractId": d2["contractId"], "serviceCode": "RENTAL-FLEX", "category": "OUTAGE", "description": "pane"}).json()
    c.post(f"/api/v1/support/tickets/{t['ticketId']}/resolve", headers=H)
    doc = yaml.safe_load(open(SP / "iso/docs/events/asyncapi.yaml"))
    reg = Registry().with_resource("urn:a", Resource(contents=doc, specification=DRAFT202012))
    names = {m["name"]: k for k, m in doc["components"]["messages"].items()}
    with SessionLocal() as s:
        for e in s.scalars(select(OutboxEvent).where(OutboxEvent.event_type.in_(["ContractActivated.v1", "TicketResolved.v1"]))):
            env = e.envelope()
            for fc in (None, FormatChecker()):
                v = Draft202012Validator({"$ref": f"urn:a#/components/messages/{names[env['eventType']]}/payload"}, registry=reg, format_checker=fc)
                errs = [x.message for x in v.iter_errors(env)]
                print(f"  {env['eventType']} formatchecker={'on' if fc else 'off'} amount={env['payload'].get('billing',{}).get('amount')} dueAt={env['payload'].get('dueAt')} erros={errs}")
    import jsonschema
    for val in (100.1, 100.10, 0.07, 19.99, 2500.0, 1234567.89):
        errs = [x.message for x in Draft202012Validator(doc["components"]["schemas"]["Money"]).iter_errors({"amount": val, "currency": "BRL", "cycle": "ONCE"})]
        print(f"  Money.amount={val!r} multipleOf 0.01 -> erros={errs}")
