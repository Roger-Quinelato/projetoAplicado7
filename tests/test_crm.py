import pytest

from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import AuditLog, OutboxEvent

MISSING_ID = "99999999-9999-4999-8999-999999999999"


def token(role: str) -> dict:
    return {"Authorization": f"Bearer demo-{role}"}


@pytest.fixture
def customer(client, admin_headers):
    response = client.post("/api/v1/crm/customers", headers=admin_headers, json={
        "name": "  Cliente CRM Sintético  ", "email": "crm@example.com", "legacyId": "SINT-CRM-1",
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_cliente_criado_normaliza_nome_e_expoe_consentimento(customer):
    assert customer["name"] == "Cliente CRM Sintético"
    assert customer["eligible"] is True
    assert customer["consentService"] is True
    assert customer["active"] is True
    assert customer["legacyId"] == "SINT-CRM-1"


def test_listagem_de_clientes_filtra_e_pagina(client, admin_headers, customer):
    client.post("/api/v1/crm/customers", headers=admin_headers, json={"name": "Outro Cliente", "email": "outro@example.com"})
    assert [c["email"] for c in client.get("/api/v1/crm/customers", headers=admin_headers, params={"email": "crm@example.com"}).json()] == ["crm@example.com"]
    by_legacy = client.get("/api/v1/crm/customers", headers=admin_headers, params={"legacyId": "SINT-CRM-1"}).json()
    assert [c["customerId"] for c in by_legacy] == [customer["customerId"]]
    assert client.get("/api/v1/crm/customers", headers=admin_headers, params={"legacyId": "INEXISTENTE"}).json() == []
    page = client.get("/api/v1/crm/customers", headers=admin_headers, params={"limit": 1, "offset": 1}).json()
    assert len(page) == 1
    assert client.get("/api/v1/crm/customers", headers=admin_headers, params={"limit": 0}).status_code == 422


def test_atualizacao_sem_mudanca_nao_publica_evento_e_corpo_vazio_e_rejeitado(client, admin_headers, customer):
    path = f"/api/v1/crm/customers/{customer['customerId']}"
    assert client.patch(path, headers=admin_headers, json={"name": customer["name"]}).status_code == 200
    assert client.patch(path, headers=admin_headers, json={}).status_code == 422
    assert client.patch(path, headers=admin_headers, json={"name": None}).status_code == 422
    assert client.patch(path, headers=admin_headers, json={"name": "   "}).status_code == 422
    changed = client.patch(path, headers=admin_headers, json={"consentService": False})
    assert changed.json()["consentService"] is False
    with SessionLocal() as session:
        assert session.query(OutboxEvent).filter_by(event_type="CustomerUpdated.v1").count() == 0
    client.patch(path, headers=admin_headers, json={"name": "Cliente Renomeado"})
    with SessionLocal() as session:
        assert session.query(OutboxEvent).filter_by(event_type="CustomerUpdated.v1").count() == 1


def test_cliente_inativo_nao_origina_contrato(client, admin_headers, customer):
    inactive = client.post(f"/api/v1/crm/customers/{customer['customerId']}/deactivate", headers=admin_headers)
    assert inactive.status_code == 200
    assert inactive.json()["active"] is False
    assert client.get("/api/v1/crm/customers", headers=admin_headers, params={"active": False}).json()[0]["customerId"] == customer["customerId"]
    draft = client.post("/api/v1/contracts/drafts", headers={**admin_headers, "Idempotency-Key": "inactive-draft"}, json={
        "customerId": customer["customerId"], "serviceCode": "RENTAL-FLEX", "startsOn": "2027-01-04",
        "billing": {"amount": 100, "currency": "BRL", "cycle": "MONTHLY"},
    })
    assert draft.status_code == 422
    assert draft.json()["code"] == "BUSINESS_RULE_VIOLATION"


def test_contatos_crud_com_auditoria(client, admin_headers, customer):
    created = client.post("/api/v1/crm/contacts", headers=admin_headers, json={
        "customerId": customer["customerId"], "name": "Pessoa Contato", "email": "contato@example.com", "phone": "+5531999990000",
    })
    assert created.status_code == 201, created.text
    contact_id = created.json()["contactId"]
    path = f"/api/v1/crm/contacts/{contact_id}"
    assert client.get(path, headers=admin_headers).json()["phone"] == "+5531999990000"
    updated = client.patch(path, headers=admin_headers, json={"phone": None, "name": "Pessoa Atualizada"})
    assert updated.json()["phone"] is None
    assert updated.json()["name"] == "Pessoa Atualizada"
    listed = client.get("/api/v1/crm/contacts", headers=admin_headers, params={"customerId": customer["customerId"]}).json()
    assert [c["contactId"] for c in listed] == [contact_id]
    assert client.delete(path, headers=admin_headers).status_code == 204
    assert client.get(path, headers=admin_headers).status_code == 404
    with SessionLocal() as session:
        operations = {entry.operation for entry in session.query(AuditLog).filter_by(module="crm")}
    assert {"create_contact", "update_contact", "delete_contact"}.issubset(operations)


def test_contato_valida_telefone_email_duplicado_e_cliente(client, admin_headers, customer):
    body = {"customerId": customer["customerId"], "name": "Pessoa Contato", "email": "contato@example.com"}
    assert client.post("/api/v1/crm/contacts", headers=admin_headers, json={**body, "phone": "31 9999-0000"}).status_code == 422
    assert client.post("/api/v1/crm/contacts", headers=admin_headers, json=body).status_code == 201
    duplicate = client.post("/api/v1/crm/contacts", headers=admin_headers, json=body)
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "CONFLICT"
    missing = client.post("/api/v1/crm/contacts", headers=admin_headers, json={**body, "customerId": MISSING_ID})
    assert missing.status_code == 404


def test_oportunidade_respeita_transicoes(client, admin_headers, customer):
    created = client.post("/api/v1/crm/opportunities", headers=admin_headers, json={
        "customerId": customer["customerId"], "title": "Renovação de frota", "notes": "Primeira proposta",
    })
    assert created.status_code == 201
    path = f"/api/v1/crm/opportunities/{created.json()['opportunityId']}"
    assert client.patch(path, headers=admin_headers, json={"title": "Renovação de frota 2027"}).json()["title"] == "Renovação de frota 2027"
    assert client.patch(path, headers=admin_headers, json={"status": "WON"}).json()["status"] == "WON"
    assert client.patch(path, headers=admin_headers, json={"status": "WON"}).status_code == 200
    reopen = client.patch(path, headers=admin_headers, json={"status": "OPEN"})
    assert reopen.status_code == 409
    assert reopen.json()["code"] == "INVALID_STATE"
    assert client.patch(path, headers=admin_headers, json={"notes": "Depois de ganha"}).status_code == 409
    assert client.get("/api/v1/crm/opportunities", headers=admin_headers, params={"status": "WON"}).json()[0]["status"] == "WON"
    assert client.patch(path, headers=admin_headers, json={"status": "CLOSED"}).status_code == 422
    too_long = client.post("/api/v1/crm/opportunities", headers=admin_headers, json={
        "customerId": customer["customerId"], "title": "Longa", "notes": "x" * 2001,
    })
    assert too_long.status_code == 422


@pytest.mark.parametrize("path", [
    f"/api/v1/crm/customers/{MISSING_ID}",
    f"/api/v1/crm/contacts/{MISSING_ID}",
    f"/api/v1/crm/opportunities/{MISSING_ID}",
])
def test_recursos_inexistentes_retornam_404(client, admin_headers, path):
    response = client.get(path, headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.parametrize(("method", "path", "allowed", "denied"), [
    ("get", "/api/v1/crm/customers", {"commercial", "contracts", "support"}, {"finance", "operations"}),
    ("post", "/api/v1/crm/customers", {"commercial"}, {"contracts", "finance", "support", "operations"}),
    ("get", "/api/v1/crm/contacts", {"commercial"}, {"contracts", "finance", "support", "operations"}),
    ("get", "/api/v1/crm/opportunities", {"commercial"}, {"contracts", "finance", "support", "operations"}),
])
def test_matriz_de_autorizacao_do_crm(client, method, path, allowed, denied):
    body = {"name": "Cliente Papel", "email": "papel@example.com"} if method == "post" else None
    assert getattr(client, method)(path, **({"json": body} if body else {})).status_code == 401
    for role in allowed:
        response = client.request(method.upper(), path, headers=token(role), json=body)
        assert response.status_code in {200, 201, 409}, (role, response.text)
    for role in denied:
        response = client.request(method.upper(), path, headers=token(role), json=body)
        assert response.status_code == 403, role
        assert response.json()["code"] == "FORBIDDEN"
