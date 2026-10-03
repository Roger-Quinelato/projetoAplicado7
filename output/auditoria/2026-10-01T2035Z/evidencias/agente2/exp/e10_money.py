from harness import *
import yaml, json
from sqlalchemy import select
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import OutboxEvent
with client() as c:
    cust = customer(c); d = draft(c, cust, "M1", amount=19.99).json()
    a = activate(c, d["contractId"], "M1-A").json()
    print("resposta POST /drafts billing:", d["billing"], "| POST /activate billing:", a["billing"], "| GET /contracts/{id} billing:", c.get(f"/api/v1/contracts/{d['contractId']}", headers=H).json()["billing"])
    doc = yaml.safe_load(open(SP / "iso/docs/events/asyncapi.yaml"))
    reg = Registry().with_resource("urn:a", Resource(contents=doc, specification=DRAFT202012))
    with SessionLocal() as s:
        env = s.get(OutboxEvent, a["eventId"]).envelope()
    v = Draft202012Validator({"$ref": "urn:a#/components/messages/ContractActivated/payload"}, registry=reg)
    print("envelope real ContractActivated.v1 amount=", env["payload"]["billing"]["amount"], "erros AsyncAPI:", [e.message for e in v.iter_errors(env)])
    print("dispatch:", dispatch(c).json())
    print("fatura:", c.get("/api/v1/finance/invoices", headers=H).json()[0]["amount"])
    gen = app.openapi()["components"]["schemas"]
    print("OpenAPI Billing.amount:", json.dumps(gen["Billing"]["properties"]["amount"]))
    print("OpenAPI BillingResponse.amount:", json.dumps(gen["BillingResponse"]["properties"]["amount"]))
    print("OpenAPI InvoiceResponse.amount:", json.dumps(gen["InvoiceResponse"]["properties"]["amount"]))
    print("OpenAPI PaymentInput.amount:", json.dumps(gen["PaymentInput"]["properties"]["amount"]))
    print("ContractDraftResponse.billing:", json.dumps(gen["ContractDraftResponse"]["properties"]["billing"]))
