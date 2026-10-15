from harness import *
from datetime import date, timedelta
from sqlalchemy import select, text
from archcorp.infrastructure.db import SessionLocal, engine
from archcorp.finance.models import Invoice, Payment
def pay(c, inv, amount, ref, cur="BRL"):
    return c.post(f"/api/v1/finance/invoices/{inv}/payments", headers=H, json={"amount": amount, "currency": cur, "reference": ref})
with client() as c:
    cust = customer(c); d = draft(c, cust, "PG", amount=100.10).json(); activate(c, d["contractId"], "PG-A"); dispatch(c)
    inv = c.get("/api/v1/finance/invoices", headers=H).json()[0]; iid = inv["invoiceId"]
    show("fatura", c.get(f"/api/v1/finance/invoices/{iid}", headers=H))
    show("pag 0.001 (3 casas)", pay(c, iid, 0.001, "REF-0001"))
    show("pag 0.004 (3 casas)", pay(c, iid, "0.004", "REF-0004"))
    show("pag -1", pay(c, iid, -1, "REF-NEG"))
    show("pag 0", pay(c, iid, 0, "REF-ZERO"))
    show("pag moeda USD", pay(c, iid, 1, "REF-USD", "USD"))
    show("pag moeda 'brl' minúscula", pay(c, iid, 1, "REF-brl", "brl"))
    show("pag 100.10 (deveria exceder pois ja ha 0.005 pago)", pay(c, iid, 100.10, "REF-FULL"))
    show("pag 100.09", pay(c, iid, 100.09, "REF-10009"))
    show("pag 0.01 restante", pay(c, iid, 0.01, "REF-001"))
    show("fatura apos", c.get(f"/api/v1/finance/invoices/{iid}", headers=H))
    show("pagamentos", c.get("/api/v1/finance/payments", headers=H))
    with engine.connect() as conn:
        print("  SQLite finance_payments:", conn.execute(text("select reference, typeof(amount), amount from finance_payments")).all())
    show("pag acima do saldo", pay(c, iid, 5, "REF-OVER"))
    show("mesma referencia valor diferente", pay(c, iid, 0.02, "REF-001"))
    show("mesma referencia mesmo valor (replay)", pay(c, iid, 0.01, "REF-001"))
    # inadimplencia: fatura vencida
    cust2 = customer(c); d2 = draft(c, cust2, "PG2", amount=50).json(); activate(c, d2["contractId"], "PG2-A"); dispatch(c)
    with SessionLocal() as s:
        i2 = s.scalar(select(Invoice).where(Invoice.contract_id == d2["contractId"])); i2.due_date = date.today() - timedelta(days=1); s.commit(); i2id = i2.invoice_id
    show("fatura vencida (status calculado)", c.get(f"/api/v1/finance/invoices/{i2id}", headers=H))
    with SessionLocal() as s:
        print("  status persistido:", s.get(Invoice, i2id).status)
    show("pagamento de fatura vencida", pay(c, i2id, 50, "REF-LATE"))
    # encerramento do contrato -> efeito na fatura
    cust3 = customer(c); d3 = draft(c, cust3, "PG3", amount=70).json(); activate(c, d3["contractId"], "PG3-A"); dispatch(c)
    show("encerrar contrato", c.post(f"/api/v1/contracts/{d3['contractId']}/close", headers={**H, "Idempotency-Key": "CL3"}, json={"reason": "Devolução"}))
    show("dispatch", dispatch(c))
    show("faturas do contrato encerrado", c.get("/api/v1/finance/invoices", headers=H))
    # pagamento sem Idempotency-Key: audit? correlação?
    with SessionLocal() as s:
        print("  auditoria finance:", [(a.operation) for a in s.execute(text("select operation from integration_audit where module='finance'"))])
