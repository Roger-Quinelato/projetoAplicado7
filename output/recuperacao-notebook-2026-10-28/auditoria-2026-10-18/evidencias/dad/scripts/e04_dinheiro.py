"""E-04 (Q-06 = AUD-35, AUD-09, Q-04): valores monetários na API v1 (SQLite executado).

PostgreSQL (NÃO executado localmente): ADB_URL=postgresql+psycopg://... (banco descartável). Previsão pela inspeção
e pelo log de 01/10: drafts e reservas aceitam 1e12 e 1e15; o INSERT em Numeric(14,2) recusa e a rota responde 500.
Pagamentos têm teto de dígitos e de saldo, então não chegam ao INSERT com valor acima do limite.
"""
import os
from datetime import date, timedelta

from dad_common import H, activate, customer, dispatch, draft, reset_db, rows, setup, show

setup("e04.db")
from fastapi.testclient import TestClient  # noqa: E402

from archcorp.main import app  # noqa: E402

VALORES = [0.001, 0.005, 2500.10, 1e12, 1e15]
if os.environ.get("ADB_URL"):
    reset_db()
with TestClient(app, raise_server_exceptions=False) as c:
    cust = customer(c, "money")
    print("== drafts: billing.amount")
    for i, v in enumerate(VALORES):
        starts = (date(2027, 6, 1) + timedelta(days=i)).isoformat()
        show(f"draft {v!r}", draft(c, cust, f"E04-D-{i}", amount=v, starts=starts))
    print("== reservas: amount")
    for i, v in enumerate(VALORES):
        inicio = date(2027, 8, 1) + timedelta(days=i)
        corpo = {"customerId": cust["customerId"], "vehicleGroup": "SUV", "protectionCode": "BASICA",
                 "serviceCode": "RENTAL-FLEX", "startsOn": inicio.isoformat(),
                 "endsOn": (inicio + timedelta(days=2)).isoformat(), "amount": v, "currency": "BRL",
                 "billingCycle": "ONCE", "slaHours": 8}
        show(f"reserva {v!r}", c.post("/api/v1/contracts/reservations",
                                      headers={**H, "Idempotency-Key": f"E04-R-{i}"}, json=corpo))
    print("== pagamentos sobre fatura de 100.10")
    cid = draft(c, customer(c, "pay"), "E04-P-DRAFT", amount=100.10, starts="2027-09-01").json()["contractId"]
    activate(c, cid, "E04-P-ACT")
    dispatch(c)
    inv = c.get("/api/v1/finance/invoices", headers=H, params={"contractId": cid}).json()[0]["invoiceId"]
    for i, v in enumerate([0.001, 0.005, 1e12, 1e15, 0.01, 100.09]):
        show(f"pagamento {v!r}", c.post(f"/api/v1/finance/invoices/{inv}/payments",
                                        headers={**H, "Idempotency-Key": f"E04-PAY-{i}"},
                                        json={"amount": v, "currency": "BRL", "reference": f"E04-REF-{i}"}))
    print("fatura final:", c.get(f"/api/v1/finance/invoices/{inv}", headers=H).json()["status"])
    print("pagamentos gravados (amount, reference):", rows("SELECT amount, reference FROM finance_payments ORDER BY reference"))
    print("valores gravados em contracts_contracts:", rows("SELECT amount FROM contracts_contracts"))
