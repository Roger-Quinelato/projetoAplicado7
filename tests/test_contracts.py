from datetime import date, timedelta

import pytest

from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import AuditLog, OutboxEvent

MISSING_ID = "99999999-9999-4999-8999-999999999999"
DRAFT = {"serviceCode": "RENTAL-FLEX", "startsOn": "2027-01-04", "billing": {"amount": 2500, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8}


def future(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def reservation_body(customer_id: str, **overrides) -> dict:
    return {"customerId": customer_id, "vehicleGroup": "SUV-COMPACTO", "protectionCode": "BASICA", "serviceCode": "RENTAL-FLEX",
            "startsOn": future(3), "endsOn": future(6), "amount": 750, "currency": "BRL", "billingCycle": "ONCE", "slaHours": 8, **overrides}


@pytest.fixture
def customer(client, admin_headers):
    return client.post("/api/v1/crm/customers", headers=admin_headers, json={"name": "Cliente Contratos", "email": "contratos@example.com"}).json()


@pytest.fixture
def active_contract(client, admin_headers, customer):
    draft = client.post("/api/v1/contracts/drafts", headers={**admin_headers, "Idempotency-Key": "t09-draft"}, json={"customerId": customer["customerId"], **DRAFT}).json()
    client.post(f"/api/v1/contracts/{draft['contractId']}/activate", headers={**admin_headers, "Idempotency-Key": "t09-activate"})
    return draft


def test_rascunho_rejeita_cliente_sem_consentimento_ou_inelegivel(client, admin_headers, customer):
    for index, change in enumerate(({"consentService": False}, {"eligible": False})):
        other = client.post("/api/v1/crm/customers", headers=admin_headers, json={"name": f"Cliente {index}", "email": f"c{index}@example.com", **change}).json()
        response = client.post("/api/v1/contracts/drafts", headers={**admin_headers, "Idempotency-Key": f"rule-{index}"}, json={"customerId": other["customerId"], **DRAFT})
        assert response.status_code == 422
        assert response.json()["code"] == "BUSINESS_RULE_VIOLATION"


def test_idempotencia_do_rascunho_compara_todo_o_pedido(client, admin_headers, customer):
    headers = {**admin_headers, "Idempotency-Key": "t09-idem"}
    first = client.post("/api/v1/contracts/drafts", headers=headers, json={"customerId": customer["customerId"], **DRAFT})
    assert first.status_code == 201
    same_amount = client.post("/api/v1/contracts/drafts", headers=headers, json={"customerId": customer["customerId"], **DRAFT, "billing": {**DRAFT["billing"], "amount": "2500.00"}})
    assert same_amount.headers["Idempotency-Replayed"] == "true"
    other_sla = client.post("/api/v1/contracts/drafts", headers=headers, json={"customerId": customer["customerId"], **DRAFT, "slaHours": 4})
    assert other_sla.status_code == 409
    assert other_sla.json()["code"] == "IDEMPOTENCY_CONFLICT"
    duplicate = client.post("/api/v1/contracts/drafts", headers={**admin_headers, "Idempotency-Key": "t09-other"}, json={"customerId": customer["customerId"], **DRAFT})
    assert duplicate.status_code == 409
    assert first.json()["contractId"] in duplicate.json()["detail"]
    assert client.post("/api/v1/contracts/drafts", headers=admin_headers, json={"customerId": customer["customerId"], **DRAFT}).status_code == 422
    too_long = client.post("/api/v1/contracts/drafts", headers={**admin_headers, "Idempotency-Key": "k" * 101}, json={"customerId": customer["customerId"], **DRAFT})
    assert too_long.status_code == 422


def test_ativacao_revalida_cliente(client, admin_headers, customer):
    draft = client.post("/api/v1/contracts/drafts", headers={**admin_headers, "Idempotency-Key": "revalidate"}, json={"customerId": customer["customerId"], **DRAFT}).json()
    client.patch(f"/api/v1/crm/customers/{customer['customerId']}", headers=admin_headers, json={"consentService": False})
    response = client.post(f"/api/v1/contracts/{draft['contractId']}/activate", headers={**admin_headers, "Idempotency-Key": "revalidate-activate"})
    assert response.status_code == 422
    assert client.get(f"/api/v1/contracts/{draft['contractId']}", headers=admin_headers).json()["status"] == "DRAFT"
    assert client.post(f"/api/v1/contracts/{MISSING_ID}/activate", headers={**admin_headers, "Idempotency-Key": "missing"}).status_code == 404


def test_reserva_valida_periodo_cliente_e_idempotencia(client, admin_headers, customer):
    path = "/api/v1/contracts/reservations"
    assert client.post(path, headers=admin_headers, json=reservation_body(customer["customerId"], endsOn=future(1))).status_code == 422
    assert client.post(path, headers=admin_headers, json=reservation_body(customer["customerId"], startsOn=future(-1))).status_code == 422
    assert client.post(path, headers=admin_headers, json=reservation_body(customer["customerId"], currency="brl")).status_code == 422
    assert client.post(path, headers=admin_headers, json=reservation_body(customer["customerId"], amount=10.555)).status_code == 422
    assert client.post(path, headers=admin_headers, json=reservation_body(MISSING_ID)).status_code == 404
    headers = {**admin_headers, "Idempotency-Key": "reservation-1"}
    first = client.post(path, headers=headers, json=reservation_body(customer["customerId"], billingCycle="QUARTERLY"))
    assert first.status_code == 201, first.text
    repeated = client.post(path, headers=headers, json=reservation_body(customer["customerId"], billingCycle="QUARTERLY"))
    assert repeated.headers["Idempotency-Replayed"] == "true"
    assert repeated.json()["reservationId"] == first.json()["reservationId"]
    assert client.post(path, headers=headers, json=reservation_body(customer["customerId"], amount=800)).status_code == 409
    assert len(client.get(path, headers=admin_headers, params={"customerId": customer["customerId"]}).json()) == 1


def test_cancelamento_de_reserva_cancela_rascunho(client, admin_headers, customer):
    reservation = client.post("/api/v1/contracts/reservations", headers=admin_headers, json=reservation_body(customer["customerId"])).json()
    drafted = client.post(f"/api/v1/contracts/reservations/{reservation['reservationId']}/draft", headers={**admin_headers, "Idempotency-Key": "cancel-draft"}).json()
    contract_id = drafted["contract"]["contractId"]
    assert drafted["contract"]["endsOn"] == reservation["endsOn"]
    cancelled = client.post(f"/api/v1/contracts/reservations/{reservation['reservationId']}/cancel", headers=admin_headers)
    assert cancelled.json()["status"] == "CANCELLED"
    assert client.get(f"/api/v1/contracts/{contract_id}", headers=admin_headers).json()["status"] == "CANCELLED"
    activate = client.post(f"/api/v1/contracts/{contract_id}/activate", headers={**admin_headers, "Idempotency-Key": "after-cancel"})
    assert activate.status_code == 409
    assert activate.json()["code"] == "INVALID_STATE"
    assert client.post(f"/api/v1/contracts/reservations/{MISSING_ID}/cancel", headers=admin_headers).status_code == 404


def test_encerramento_idempotente_publica_evento_e_conclui_workflow(client, admin_headers, active_contract):
    contract_id = active_contract["contractId"]
    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    headers = {**admin_headers, "Idempotency-Key": "t09-close"}
    body = {"endsOn": "2027-02-01", "reason": "Devolução do veículo"}
    closed = client.post(f"/api/v1/contracts/{contract_id}/close", headers=headers, json=body)
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "CLOSED"
    assert closed.json()["endsOn"] == "2027-02-01"
    repeated = client.post(f"/api/v1/contracts/{contract_id}/close", headers=headers, json=body)
    assert repeated.headers["Idempotency-Replayed"] == "true"
    assert repeated.json()["eventId"] == closed.json()["eventId"]
    other_key = client.post(f"/api/v1/contracts/{contract_id}/close", headers={**admin_headers, "Idempotency-Key": "t09-close-2"}, json=body)
    assert other_key.json()["eventId"] == closed.json()["eventId"]
    assert client.post(f"/api/v1/contracts/{contract_id}/close", headers=admin_headers).status_code == 409
    assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json() == {"processed": 1, "failed": 0}
    with SessionLocal() as session:
        assert session.query(OutboxEvent).filter_by(event_type="ContractClosed.v1").count() == 1
        assert session.query(AuditLog).filter_by(operation="close_contract").count() == 1
    process = next(p for p in client.get("/api/v1/workflow/processes", headers=admin_headers).json() if p["referenceId"] == contract_id)
    assert process["state"] == "COMPLETED"


def test_encerramento_valida_estado_e_data(client, admin_headers, customer, active_contract):
    before_start = client.post(f"/api/v1/contracts/{active_contract['contractId']}/close", headers=admin_headers, json={"endsOn": "2026-12-31"})
    assert before_start.status_code == 422
    draft = client.post("/api/v1/contracts/drafts", headers={**admin_headers, "Idempotency-Key": "draft-close"}, json={"customerId": customer["customerId"], **DRAFT, "startsOn": "2027-03-01"}).json()
    response = client.post(f"/api/v1/contracts/{draft['contractId']}/close", headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["detail"] == "Somente contrato ativo pode ser encerrado"
    assert client.post(f"/api/v1/contracts/{MISSING_ID}/close", headers=admin_headers).status_code == 404


@pytest.mark.parametrize(("path", "denied"), [
    ("/api/v1/contracts/{contract}/activate", ["commercial", "finance", "support", "operations"]),
    ("/api/v1/contracts/{contract}/close", ["commercial", "finance", "support", "operations"]),
    ("/api/v1/contracts/reservations", ["finance", "support", "operations"]),
])
def test_matriz_de_autorizacao_de_contratos(client, active_contract, path, denied):
    url = path.format(contract=active_contract["contractId"])
    assert client.post(url, headers={"Idempotency-Key": "auth"}).status_code == 401
    for role in denied:
        response = client.post(url, headers={"Authorization": f"Bearer demo-{role}", "Idempotency-Key": "auth"}, json={})
        assert response.status_code == 403, role


def test_leitura_de_contratos_por_papel(client, active_contract):
    url = f"/api/v1/contracts/{active_contract['contractId']}"
    for role in ("commercial", "contracts", "finance", "support"):
        assert client.get(url, headers={"Authorization": f"Bearer demo-{role}"}).status_code == 200, role
    assert client.get(url, headers={"Authorization": "Bearer demo-operations"}).status_code == 403
