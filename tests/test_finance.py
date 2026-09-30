from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from archcorp.finance.models import Invoice, Payment
from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import AuditLog


@pytest.fixture
def invoice(client, admin_headers, integrated_contract):
    _, contract = integrated_contract
    assert client.post(f"/api/v1/contracts/{contract['contractId']}/activate",
                       headers={**admin_headers, "Idempotency-Key": "finance-activation"}).status_code == 200
    assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json()["processed"] == 1
    return client.get("/api/v1/finance/invoices", headers=admin_headers).json()[0]


@pytest.mark.parametrize("amount", ["0.001", "1.999", "0", "-1"])
def test_pagamento_rejeita_valor_invalido(client, admin_headers, invoice, amount):
    response = client.post(f"/api/v1/finance/invoices/{invoice['invoiceId']}/payments", headers=admin_headers,
                           json={"amount": amount, "currency": "BRL", "reference": "SIM-INVALID"})
    assert response.status_code == 422
    assert client.get("/api/v1/finance/payments", headers=admin_headers).json() == []


def test_pagamentos_parciais_idempotentes_e_auditados(client, admin_headers, invoice):
    path = f"/api/v1/finance/invoices/{invoice['invoiceId']}/payments"
    first = {"amount": "1000.00", "currency": "BRL", "reference": "SIM-PARTIAL"}
    paid = client.post(path, headers=admin_headers, json=first)
    assert paid.status_code == 201
    assert paid.json()["invoice"]["paidAmount"] == 1000
    assert paid.json()["invoice"]["status"] == "OPEN"
    repeated = client.post(path, headers=admin_headers, json=first)
    assert repeated.json() == paid.json()
    assert client.post(path, headers=admin_headers, json={**first, "amount": "1001"}).status_code == 409
    assert client.post(path, headers=admin_headers, json={**first, "reference": "SIM-OVER", "amount": "1500.01"}).status_code == 409
    assert client.post(path, headers=admin_headers, json={**first, "currency": "USD"}).status_code == 422
    completed = client.post(path, headers=admin_headers, json={**first, "reference": "SIM-FINAL", "amount": "1500.00"})
    assert completed.json()["invoice"]["status"] == "PAID"
    assert client.post(path, headers=admin_headers, json={**first, "reference": "SIM-AFTER"}).status_code == 409
    with SessionLocal() as session:
        payments = session.scalars(select(Payment)).all()
        logs = session.scalars(select(AuditLog).where(AuditLog.operation == "record_payment")).all()
        assert len(payments) == len(logs) == 2
        assert {p.payment_id for p in payments} == {log.entity_id for log in logs}
        assert sum((p.amount for p in payments), Decimal("0")) == Decimal("2500.00")
        assert all(log.correlation_id == admin_headers["X-Correlation-ID"] for log in logs)


def test_inadimplencia_por_vencimento_e_quitacao(client, admin_headers, invoice):
    path = f"/api/v1/finance/invoices/{invoice['invoiceId']}"
    with SessionLocal() as session:
        item = session.get(Invoice, invoice["invoiceId"])
        item.due_date = date.today()
        session.commit()
    assert client.get(path, headers=admin_headers).json()["status"] == "OPEN"
    with SessionLocal() as session:
        session.get(Invoice, invoice["invoiceId"]).due_date = date.today() - timedelta(days=1)
        session.commit()
    assert client.get(path, headers=admin_headers).json()["status"] == "OVERDUE"
    assert client.get("/api/v1/finance/invoices", headers=admin_headers).json()[0]["status"] == "OVERDUE"
    assert client.post(path + "/payments", headers=admin_headers, json={
        "amount": "2500", "currency": "BRL", "reference": "SIM-SETTLED",
    }).json()["invoice"]["status"] == "PAID"
    assert client.get(path, headers=admin_headers).json()["status"] == "PAID"


def test_finance_autorizacao(client, admin_headers, invoice):
    path = f"/api/v1/finance/invoices/{invoice['invoiceId']}/payments"
    body = {"amount": "1", "currency": "BRL", "reference": "SIM-ROLE"}
    assert client.post(path, json=body).status_code == 401
    assert client.post(path, headers={"Authorization": "Bearer demo-operations"}, json=body).status_code == 403
    assert client.post(path, headers={"Authorization": "Bearer demo-finance"}, json=body).status_code == 201
