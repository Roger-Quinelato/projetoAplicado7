import pytest

from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import IdempotencyRecord, OutboxEvent
from archcorp.support.models import Ticket


@pytest.mark.parametrize("legacy", [False, True])
def test_abertura_compara_descricao_e_preserva_replay(client, admin_headers, integrated_contract, legacy):
    customer, contract = integrated_contract
    client.post(f"/api/v1/contracts/{contract['contractId']}/activate",
                headers={**admin_headers, "Idempotency-Key": "support-activate"})
    headers = {**admin_headers, "Idempotency-Key": "support-description"}
    body = {"customerId": customer["customerId"], "contractId": contract["contractId"],
            "serviceCode": "RENTAL-FLEX", "category": "QUESTION", "description": "Dúvida sintética inicial"}
    first = client.post("/api/v1/support/tickets", headers=headers, json=body)
    assert first.status_code == 201
    if legacy:
        with SessionLocal() as session:
            record = session.get(IdempotencyRecord, {"key": "support-description", "operation": "open_ticket"})
            record.request_hash = None
            session.commit()
    repeated = client.post("/api/v1/support/tickets", headers=headers, json=body)
    assert repeated.json() == first.json()
    assert repeated.headers["Idempotency-Replayed"] == "true"
    conflict = client.post("/api/v1/support/tickets", headers=headers,
                           json={**body, "description": "Outro pedido sintético"})
    if legacy:
        # Registro anterior à impressão digital compara só os campos legados
        # (IdempotencyStore.save_legacy): a descrição não entra e o pedido é replay.
        assert conflict.json() == first.json()
        assert conflict.headers["Idempotency-Replayed"] == "true"
    else:
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"
    with SessionLocal() as session:
        assert session.query(Ticket).count() == 1
        assert session.query(OutboxEvent).filter_by(event_type="TicketOpened.v1").count() == 1
