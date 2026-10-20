"""Integridade de F2/F3 na mesma versão (plano de conclusão, pacote D; #60).

Complementa `test_finance.py`, `test_t15_atendimento.py` e `test_migration_convergence.py`, que já cobrem
centavos, saldo, cancelamento, ciclos iniciados, reentrega por `eventId` e o bloqueio do downgrade.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select

from archcorp.exceptions import ConflictError
from archcorp.finance.routes import finance_service
from archcorp.infrastructure.db import SessionLocal, engine
from archcorp.integration.models import OutboxEvent
from archcorp.integration.public import enqueue
from archcorp.main import contracts


def _activate_and_dispatch(client, headers, contract_id):
    assert client.post(f"/api/v1/contracts/{contract_id}/activate", headers={**headers, "Idempotency-Key": f"d-{contract_id}"}).status_code == 200
    assert client.post("/api/v1/integration/outbox/dispatch", headers=headers).json() == {"processed": 1, "failed": 0}


def _republish(event_type: str, reference_field: str, reference_id: str) -> None:
    """Grava outro evento (novo eventId) para o mesmo fato já publicado, como faria um produtor repetido."""
    with SessionLocal() as session:
        original = next(e for e in session.scalars(select(OutboxEvent).where(OutboxEvent.event_type == event_type))
                        if e.payload[reference_field] == reference_id)
        enqueue(session, event_type, original.producer, dict(original.payload), str(uuid4()))
        session.commit()


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _processes(client, headers, process_type, reference_id):
    return [p for p in client.get("/api/v1/workflow/processes", headers=headers).json()
            if p["processType"] == process_type and p["referenceId"] == reference_id]


def test_encerramento_sem_data_usa_a_data_utc(client, admin_headers, integrated_contract, monkeypatch):
    _, contract = integrated_contract
    _activate_and_dispatch(client, admin_headers, contract["contractId"])
    # 31/12 às 23h30 em Brasília já é 01/01 em UTC: a data padrão não depende do fuso do servidor.
    monkeypatch.setattr(contracts, "clock", lambda: datetime(2027, 1, 1, 2, 30, tzinfo=timezone.utc))
    closed = client.post(f"/api/v1/contracts/{contract['contractId']}/close", headers={**admin_headers, "Idempotency-Key": "d-close"}, json={})
    assert closed.status_code == 200, closed.text
    assert closed.json()["endsOn"] == "2027-01-01"


def test_novo_evento_do_mesmo_fato_nao_duplica_fatura_nem_preparacao(client, admin_headers, integrated_contract):
    _, contract = integrated_contract
    contract_id = contract["contractId"]
    _activate_and_dispatch(client, admin_headers, contract_id)
    _republish("ContractActivated.v1", "contractId", contract_id)

    assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json() == {"processed": 1, "failed": 0}
    invoices = client.get("/api/v1/finance/invoices", headers=admin_headers, params={"contractId": contract_id}).json()
    assert [i["kind"] for i in invoices] == ["INITIAL"]
    assert len(_processes(client, admin_headers, "ONBOARDING", contract_id)) == 1


def test_novo_evento_do_mesmo_chamado_nao_duplica_resolucao(client, admin_headers, integrated_contract):
    customer, contract = integrated_contract
    _activate_and_dispatch(client, admin_headers, contract["contractId"])
    ticket = client.post("/api/v1/support/tickets", headers={**admin_headers, "Idempotency-Key": "d-ticket"}, json={
        "customerId": customer["customerId"], "contractId": contract["contractId"], "serviceCode": "RENTAL-FLEX",
        "category": "OUTAGE", "description": "Chamado sintético",
    }).json()
    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    _republish("TicketOpened.v1", "ticketId", ticket["ticketId"])

    assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json() == {"processed": 1, "failed": 0}
    [process] = _processes(client, admin_headers, "TICKET_RESOLUTION", ticket["ticketId"])
    assert _utc(process["dueAt"]) == _utc(ticket["dueAt"])


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="Exige PostgreSQL real")
def test_pagamentos_concorrentes_nao_excedem_o_saldo(client, admin_headers, integrated_contract):
    _, contract = integrated_contract
    _activate_and_dispatch(client, admin_headers, contract["contractId"])
    [invoice] = client.get("/api/v1/finance/invoices", headers=admin_headers, params={"contractId": contract["contractId"]}).json()
    barrier = Barrier(2)
    service = finance_service()

    def pay(reference):
        with SessionLocal() as session:
            barrier.wait(timeout=10)
            try:
                service.record_payment(session, invoice["invoiceId"], {"amount": 1500, "currency": "BRL", "reference": reference}, None, "synthetic")
                return "ok"
            except ConflictError:
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = sorted(executor.map(pay, ["D-PG-1", "D-PG-2"]))
    assert results == ["conflict", "ok"]
    after = client.get(f"/api/v1/finance/invoices/{invoice['invoiceId']}", headers=admin_headers).json()
    assert (after["paidAmount"], after["balance"], after["status"]) == (1500.0, 1000.0, "PARTIALLY_PAID")
