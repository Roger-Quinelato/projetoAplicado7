from datetime import date, timedelta

from archcorp.config import settings


def test_reservation_to_contract_and_finance_payment(client, admin_headers):
    customer = client.post("/api/v1/crm/customers", headers=admin_headers, json={
        "name": "Cliente Sintético", "email": "sintetico@example.com"
    }).json()
    reservation = client.post("/api/v1/contracts/reservations", headers=admin_headers, json={
        "customerId": customer["customerId"], "vehicleGroup": "Economico",
        "protectionCode": "BASICA", "serviceCode": "RENTAL-FLEX",
        "startsOn": (date.today() + timedelta(days=2)).isoformat(),
        "endsOn": (date.today() + timedelta(days=5)).isoformat(), "amount": 250,
        "currency": "BRL", "billingCycle": "ONCE", "slaHours": 8,
    })
    assert reservation.status_code == 201, reservation.text
    reservation_id = reservation.json()["reservationId"]
    draft = client.post(f"/api/v1/contracts/reservations/{reservation_id}/draft",
                        headers={**admin_headers, "Idempotency-Key": "reservation-draft-1"})
    assert draft.status_code == 200, draft.text
    contract_id = draft.json()["contract"]["contractId"]
    assert client.post(f"/api/v1/contracts/{contract_id}/activate",
                       headers={**admin_headers, "Idempotency-Key": "reservation-activate-1"}).status_code == 200
    assert client.get(f"/api/v1/contracts/reservations/{reservation_id}", headers=admin_headers).json()["status"] == "ACTIVE"
    assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json()["processed"] == 1
    invoices = client.get("/api/v1/finance/invoices", headers=admin_headers).json()
    assert len(invoices) == 1
    invoice_id = invoices[0]["invoiceId"]
    paid = client.post(f"/api/v1/finance/invoices/{invoice_id}/payments", headers=admin_headers,
                       json={"amount": 250, "currency": "BRL", "reference": "SIMULATED-001"})
    assert paid.status_code == 201, paid.text
    assert paid.json()["invoice"]["status"] == "PAID"
    repeated = client.post(f"/api/v1/finance/invoices/{invoice_id}/payments", headers=admin_headers,
                           json={"amount": 250, "currency": "BRL", "reference": "SIMULATED-001"})
    assert repeated.json()["paymentId"] == paid.json()["paymentId"]
    assert len(client.get("/api/v1/finance/payments", headers=admin_headers).json()) == 1
    assert client.post(f"/api/v1/contracts/{contract_id}/close", headers=admin_headers).status_code == 200
    assert client.get(f"/api/v1/contracts/reservations/{reservation_id}", headers=admin_headers).json()["status"] == "CLOSED"
    assert client.post(f"/api/v1/contracts/{contract_id}/activate",
                       headers={**admin_headers, "Idempotency-Key": "try-reactivate"}).status_code == 409


def test_support_resolution_completes_workflow(client, admin_headers, integrated_contract):
    customer, contract = integrated_contract
    contract_id = contract["contractId"]
    client.post(f"/api/v1/contracts/{contract_id}/activate",
                headers={**admin_headers, "Idempotency-Key": "activation-for-support"})
    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    ticket = client.post("/api/v1/support/tickets",
                         headers={**admin_headers, "Idempotency-Key": "support-resolution"}, json={
        "customerId": customer["customerId"], "contractId": contract_id,
        "serviceCode": "RENTAL-FLEX", "category": "OUTAGE", "description": "Falha simulada"
    })
    assert ticket.status_code == 201, ticket.text
    ticket_id = ticket.json()["ticketId"]
    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    assert client.post(f"/api/v1/support/tickets/{ticket_id}/assign", headers=admin_headers,
                       json={"owner": "Equipe de teste"}).json()["owner"] == "Equipe de teste"
    resolved = client.post(f"/api/v1/support/tickets/{ticket_id}/resolve", headers=admin_headers)
    assert resolved.status_code == 200, resolved.text
    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    processes = client.get("/api/v1/workflow/processes", headers=admin_headers).json()
    process = next(p for p in processes if p["referenceId"] == ticket_id)
    assert process["state"] == "COMPLETED"
    tasks = client.get("/api/v1/workflow/tasks", headers=admin_headers,
                       params={"processId": process["processId"]}).json()
    assert tasks and all(task["state"] == "DONE" for task in tasks)
    assert client.post(f"/api/v1/support/tickets/{ticket_id}/reconcile", headers=admin_headers).status_code == 409


def test_public_demo_rejects_local_tokens(client, admin_headers):
    old_public, old_token = settings.public_demo, settings.demo_access_token
    settings.public_demo, settings.demo_access_token = True, "only-on-server"
    try:
        assert client.get("/api/v1/demo/state", headers=admin_headers).status_code == 401
        assert client.get("/api/v1/demo/state", headers={"Authorization": "Bearer only-on-server"}).status_code == 200
    finally:
        settings.public_demo, settings.demo_access_token = old_public, old_token
