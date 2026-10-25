import logging

import pytest
from archcorp.infrastructure.db import SessionLocal
from archcorp.crm.service import CustomerService
from archcorp.integration.models import AuditLog, InboxEvent, OutboxEvent
from archcorp.integration.service import EventDispatcher, audit


@pytest.mark.parametrize("database_failure", [False, True])
def test_falha_desfaz_efeitos_parciais_e_permanece_recuperavel(database_failure, admin_headers):
    correlation = admin_headers["X-Correlation-ID"]

    def partial_write(session, envelope):
        audit(session, correlation, "test", "partial_write", "success", envelope["eventId"])
        session.flush()

    def fail(session, envelope):
        if database_failure:
            session.add(InboxEvent(event_id=envelope["eventId"], consumer=None))
            session.flush()
        raise RuntimeError("falha sintética")

    with SessionLocal() as session:
        event = OutboxEvent(event_type="Recovery.v1", producer="test", payload={}, correlation_id=correlation)
        session.add(event)
        session.commit()
        failing = EventDispatcher({"Recovery.v1": [("writer", partial_write), ("failure", fail)]})
        assert failing.dispatch_pending(session) == {"processed": 0, "failed": 1}
        assert session.query(AuditLog).count() == session.query(InboxEvent).count() == 0
        assert event.status == "PENDING" and event.attempts == 1
        recovered = EventDispatcher({"Recovery.v1": [("writer", partial_write), ("failure", lambda *_: None)]})
        assert recovered.dispatch_pending(session) == {"processed": 1, "failed": 0}
        assert session.query(AuditLog).count() == 1
        assert session.query(InboxEvent).count() == 2
        assert event.status == "PUBLISHED" and event.last_error is None


def test_erro_nao_expoe_conteudo_da_excecao_em_fila_api_ou_log(client, admin_headers, caplog):
    marker = "SEGREDO-SINTETICO-NAO-LOGAR"

    def fail(*_):
        raise RuntimeError(marker)

    with SessionLocal() as session:
        event = OutboxEvent(event_type="Privacy.v1", producer="test", payload={},
                            correlation_id=admin_headers["X-Correlation-ID"])
        session.add(event)
        session.commit()
        dispatcher = EventDispatcher({"Privacy.v1": [("private", fail)]})
        with caplog.at_level(logging.WARNING, logger="archcorp"):
            for _ in range(3):
                dispatcher.dispatch_pending(session)
        assert event.status == "FAILED"
        assert marker not in event.last_error
        assert event.last_error.startswith("Falha no despacho do evento")
        assert marker not in caplog.text
        record = next(r for r in caplog.records if r.name == "archcorp" and r.levelno == logging.WARNING)
        assert record.correlationId == admin_headers["X-Correlation-ID"]
        assert record.errorType == "RuntimeError"
    failures = client.get("/api/v1/integration/failures", headers=admin_headers)
    assert marker not in failures.text
    assert "Falha no despacho do evento" in failures.text


def test_erro_http_nao_registra_texto_da_excecao(client, admin_headers, monkeypatch, caplog):
    marker = "CONTEUDO-SINTETICO-PRIVADO"

    def fail(*_):
        raise RuntimeError(marker)

    monkeypatch.setattr(CustomerService, "create", fail)
    with caplog.at_level(logging.ERROR, logger="archcorp"):
        response = client.post("/api/v1/crm/customers", headers=admin_headers,
                               json={"name": "Cliente Sintético", "email": "private@example.com"})
    assert response.status_code == 500
    assert marker not in response.text
    assert marker not in caplog.text
