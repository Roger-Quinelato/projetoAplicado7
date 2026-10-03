from harness import *
from sqlalchemy import text
from archcorp.infrastructure.db import engine
def pay(c, inv, amount, ref):
    return c.post(f"/api/v1/finance/invoices/{inv}/payments", headers=H, json={"amount": amount, "currency": "BRL", "reference": ref})
with client() as c:
    cust = customer(c); d = draft(c, cust, "X1", amount=100.10).json(); activate(c, d["contractId"], "X1-A"); dispatch(c)
    iid = c.get("/api/v1/finance/invoices", headers=H).json()[0]["invoiceId"]
    show("pag 100.095 (abaixo do valor, arredonda para 100.10)", pay(c, iid, "100.095", "X1-REF1"))
    show("fatura apos", c.get(f"/api/v1/finance/invoices/{iid}", headers=H))
    show("pag 0.01 restante", pay(c, iid, "0.01", "X1-REF2"))
    show("pag 0.004", pay(c, iid, "0.004", "X1-REF3"))
    show("fatura final", c.get(f"/api/v1/finance/invoices/{iid}", headers=H))
    with engine.connect() as conn:
        print("  raw:", conn.execute(text("select reference, typeof(amount), amount from finance_payments")).all())
        print("  invoice status raw:", conn.execute(text("select status, amount from finance_invoices")).all())
