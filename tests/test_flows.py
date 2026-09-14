from sqlalchemy import select

from archcorp.config import settings
from archcorp.contracts.models import Contract
from archcorp.finance.models import Invoice
from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import InboxEvent
from archcorp.integration.models import OutboxEvent
from archcorp.integration.service import EventDispatcher
from archcorp.workflow.models import ProcessInstance


def test_f1_cria_rascunho_sem_recadastro_e_reutiliza_idempotencia(client, admin_headers, integrated_contract):
    customer, contract = integrated_contract
    assert contract["customerId"] == customer["customerId"]
    assert contract["status"] == "DRAFT"
    repeated = client.post("/api/v1/contracts/drafts", headers={**admin_headers, "Idempotency-Key": "draft-1"}, json={
        "customerId": customer["customerId"], "serviceCode": "SUPPORT-PREMIUM", "startsOn": "2026-10-01",
        "billing": {"amount": 2500, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8,
    })
    assert repeated.headers["Idempotency-Replayed"] == "true"
    assert repeated.json()["contractId"] == contract["contractId"]


def test_f2_ativacao_cria_uma_cobranca_e_um_onboarding(client, admin_headers, integrated_contract):
    _, contract = integrated_contract
    headers = {**admin_headers, "Idempotency-Key": "activate-1"}
    first = client.post(f"/api/v1/contracts/{contract['contractId']}/activate", headers=headers)
    second = client.post(f"/api/v1/contracts/{contract['contractId']}/activate", headers=headers)
    assert first.status_code == 200
    assert second.headers["Idempotency-Replayed"] == "true"
    assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json()["processed"] == 1
    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    with SessionLocal() as session:
        assert session.query(Invoice).count() == 1
        assert session.query(ProcessInstance).filter_by(process_type="ONBOARDING").count() == 1
        assert session.query(InboxEvent).count() == 2


def test_f3_abre_chamado_com_sla_e_inicia_resolucao(client, admin_headers, integrated_contract):
    customer, contract = integrated_contract
    client.post(f"/api/v1/contracts/{contract['contractId']}/activate", headers={**admin_headers, "Idempotency-Key": "activate-2"})
    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    ticket = client.post("/api/v1/support/tickets", headers={**admin_headers, "Idempotency-Key": "ticket-1"}, json={
        "customerId": customer["customerId"], "contractId": contract["contractId"], "serviceCode": "SUPPORT-PREMIUM",
        "category": "OUTAGE", "description": "Serviço indisponível",
    })
    assert ticket.status_code == 201
    assert ticket.json()["status"] == "OPEN"
    assert ticket.json()["slaHours"] == 8
    assert ticket.json()["priority"] == "HIGH"
    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    with SessionLocal() as session:
        assert session.query(ProcessInstance).filter_by(process_type="TICKET_RESOLUTION").count() == 1


def test_atualizacao_cadastral_chega_a_contratos(client, admin_headers, integrated_contract):
    customer, _ = integrated_contract
    client.patch(f"/api/v1/crm/customers/{customer['customerId']}", headers=admin_headers, json={"name": "Empresa Atualizada"})
    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    with SessionLocal() as session:
        contract = session.scalar(select(Contract))
        assert contract.customer_name == "Empresa Atualizada"


def test_indisponibilidade_de_contratos_cria_estado_pendente(client, admin_headers, integrated_contract):
    customer, contract = integrated_contract
    client.post(f"/api/v1/contracts/{contract['contractId']}/activate", headers={**admin_headers, "Idempotency-Key": "activate-3"})
    settings.contract_adapter_available = False
    try:
        ticket = client.post("/api/v1/support/tickets", headers={**admin_headers, "Idempotency-Key": "ticket-pending"}, json={
            "customerId": customer["customerId"], "contractId": contract["contractId"], "serviceCode": "SUPPORT-PREMIUM",
            "category": "QUESTION", "description": "Consulta durante indisponibilidade",
        })
        assert ticket.json()["status"] == "PENDING_ENTITLEMENT"
    finally:
        settings.contract_adapter_available = True
    reconciled = client.post(f"/api/v1/support/tickets/{ticket.json()['ticketId']}/reconcile", headers=admin_headers)
    assert reconciled.json()["status"] == "OPEN"


def test_autorizacao_por_papel(client):
    response = client.post("/api/v1/crm/customers", headers={"Authorization": "Bearer demo-support"}, json={"name": "Sem permissão", "email": "x@example.com"})
    assert response.status_code == 403


def test_validacao_e_correlacao(client, admin_headers):
    response = client.post("/api/v1/crm/customers", headers=admin_headers, json={"name": "X", "email": "inválido"})
    assert response.status_code == 422
    assert response.headers["X-Correlation-ID"] == admin_headers["X-Correlation-ID"]


def test_falha_permanente_pode_ser_listada_e_reprocessada(client, admin_headers):
    def fail(_session, _event):
        raise RuntimeError("dependência simulada indisponível")

    with SessionLocal() as session:
        event = OutboxEvent(event_type="Broken.v1", producer="test", payload={}, correlation_id=admin_headers["X-Correlation-ID"])
        session.add(event)
        session.commit()
        event_id = event.event_id
        failing_dispatcher = EventDispatcher({"Broken.v1": [("broken-consumer", fail)]})
        for _ in range(settings.retry_limit):
            failing_dispatcher.dispatch_pending(session)
        session.refresh(event)
        assert event.status == "FAILED"
        assert event.attempts == settings.retry_limit
    failures = client.get("/api/v1/integration/failures", headers=admin_headers)
    assert failures.json()[0]["eventId"] == event_id
    replay = client.post(f"/api/v1/integration/failures/{event_id}/reprocess", headers=admin_headers)
    assert replay.json()["status"] == "PENDING"
