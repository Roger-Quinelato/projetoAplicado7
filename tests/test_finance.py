"""T12: fatura, pagamento simulado e inadimplência por vencimento."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from archcorp.config import settings
from archcorp.exceptions import BusinessRuleError, ConflictError, InvalidStateError
from archcorp.finance import domain
from archcorp.finance.domain import InvoiceStatus as S
from archcorp.finance.models import Invoice
from archcorp.finance.routes import finance_service
from archcorp.finance.service import FinanceService
from archcorp.infrastructure.db import SessionLocal
from archcorp.infrastructure.migrate import alembic_config
from archcorp.integration.models import InboxEvent, OutboxEvent
from archcorp.main import app

from test_foundation import assert_problem

CONTRACT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
CUSTOMER_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def fixed(moment: str):
    value = datetime.fromisoformat(moment)
    return lambda: value


def envelope(event_type: str, payload_extra: dict | None = None, *, event_id: str | None = None,
             occurred_at: str = "2026-10-14T23:30:00Z", cycle: str = "MONTHLY") -> dict:
    payload = {"contractId": CONTRACT_ID, "customerId": CUSTOMER_ID, "serviceCode": "RENTAL-FLEX", "startsOn": "2026-10-01",
               "billing": {"amount": 2500.0, "currency": "BRL", "cycle": cycle}, "slaHours": 8}
    return {"eventId": event_id or str(uuid4()), "eventType": event_type, "eventVersion": 1, "occurredAt": occurred_at,
            "correlationId": "11111111-1111-4111-8111-111111111111", "causationId": None, "producer": "contracts",
            "payload": {**payload, **(payload_extra or {})}}


def closed(ends_on: str = "2027-01-08", **kwargs) -> dict:
    return envelope("ContractClosed.v1", {"endsOn": ends_on, "status": "CLOSED", "closeReason": None}, **kwargs)


def invoices(session, kind: str | None = None) -> list[Invoice]:
    query = session.query(Invoice)
    return query.filter_by(kind=kind).all() if kind else query.all()


# ---------- Domínio ----------

@pytest.mark.parametrize("current,target,allowed", [
    (S.OPEN, S.PARTIALLY_PAID, True), (S.OPEN, S.PAID, True), (S.OPEN, S.OVERDUE, True), (S.OPEN, S.CANCELLED, True),
    (S.PARTIALLY_PAID, S.PAID, True), (S.PARTIALLY_PAID, S.OVERDUE, True), (S.PARTIALLY_PAID, S.CANCELLED, False),
    (S.OVERDUE, S.PAID, True), (S.OVERDUE, S.CANCELLED, False), (S.OVERDUE, S.OPEN, False),
    (S.PAID, S.OVERDUE, False), (S.PAID, S.CANCELLED, False), (S.CANCELLED, S.OPEN, False), (S.CANCELLED, S.PAID, False),
])
def test_transicoes_da_fatura_sao_explicitas(current, target, allowed):
    if allowed:
        domain.ensure_invoice_transition(current, target)
    else:
        with pytest.raises(InvalidStateError):
            domain.ensure_invoice_transition(current, target)


def test_estado_apos_pagamento_e_saldo():
    amount = Decimal("2500.00")
    assert domain.status_after_payment(S.OPEN, amount, Decimal("0"), Decimal("1000.00")) == S.PARTIALLY_PAID
    assert domain.status_after_payment(S.PARTIALLY_PAID, amount, Decimal("1000"), Decimal("1500.00")) == S.PAID
    assert domain.status_after_payment(S.OVERDUE, amount, Decimal("1000"), Decimal("500.00")) == S.OVERDUE
    assert domain.status_after_payment(S.OVERDUE, amount, Decimal("1000"), Decimal("1500.00")) == S.PAID
    with pytest.raises(ConflictError, match="excede saldo"):
        domain.status_after_payment(S.PARTIALLY_PAID, amount, Decimal("1000"), Decimal("1500.01"))
    with pytest.raises(ConflictError, match="quitada") as paid:
        domain.status_after_payment(S.PAID, amount, amount, Decimal("0.01"))
    assert paid.value.code == "CONFLICT"  # código da v1 preservado (não INVALID_STATE)
    with pytest.raises(InvalidStateError, match="cancelada"):
        domain.status_after_payment(S.CANCELLED, amount, Decimal("0"), Decimal("1.00"))
    with pytest.raises(BusinessRuleError):
        domain.status_after_payment(S.OPEN, amount, Decimal("0"), Decimal("0"))


def test_vencimento_usa_data_utc_e_so_vence_depois_do_dia():
    due = date(2026, 10, 24)
    balance = Decimal("10.00")
    assert not domain.is_past_due(S.OPEN, due, balance, domain.utc_today(fixed("2026-10-24T23:59:59+00:00")))
    # 24/10 às 23:30 em Brasília já é 25/10 em UTC: a regra não depende do fuso da máquina.
    assert domain.is_past_due(S.OPEN, due, balance, domain.utc_today(fixed("2026-10-24T23:30:00-03:00")))
    assert not domain.is_past_due(S.OPEN, due, Decimal("0.00"), date(2026, 10, 30))
    assert not domain.is_past_due(S.PAID, due, balance, date(2026, 10, 30))
    assert not domain.is_past_due(S.CANCELLED, due, balance, date(2026, 10, 30))
    assert domain.effective_status(S.PARTIALLY_PAID, due, balance, date(2026, 10, 25)) == S.OVERDUE
    assert domain.effective_status(S.PARTIALLY_PAID, due, balance, date(2026, 10, 24)) == S.PARTIALLY_PAID
    with pytest.raises(ValueError):
        domain.utc_today(lambda: datetime(2026, 10, 24, 12))
    assert domain.due_date_from(datetime(2026, 10, 14, 23, 30, tzinfo=timezone(timedelta(hours=-3)))) == date(2026, 10, 25)


@pytest.mark.parametrize("starts,ends,cycle,expected", [
    ("2026-10-01", "2027-01-08", "MONTHLY", 4), ("2026-10-01", "2026-11-01", "MONTHLY", 1),
    ("2026-10-01", "2026-11-02", "MONTHLY", 2), ("2026-10-01", "2026-10-01", "MONTHLY", 1),
    ("2026-01-31", "2026-03-01", "MONTHLY", 2), ("2026-10-01", "2027-01-08", "QUARTERLY", 2),
    ("2026-10-01", "2028-01-01", "YEARLY", 2), ("2026-10-01", "2027-10-01", "ONCE", 1),
])
def test_ciclos_iniciados(starts, ends, cycle, expected):
    assert domain.billed_cycles(date.fromisoformat(starts), date.fromisoformat(ends), cycle) == expected


def test_valor_final_desconta_o_ja_faturado_e_rejeita_dados_invalidos():
    start = date(2026, 10, 1)
    assert domain.final_amount(2500.0, start, date(2027, 1, 8), "MONTHLY", Decimal("2500.00")) == Decimal("7500.00")
    assert domain.final_amount(250, start, date(2026, 10, 5), "ONCE", Decimal("250")) == Decimal("0.00")
    assert domain.final_amount(100, start, date(2026, 10, 5), "MONTHLY", Decimal("300")) == Decimal("0.00")
    with pytest.raises(BusinessRuleError):
        domain.billed_cycles(start, date(2026, 9, 30), "MONTHLY")
    with pytest.raises(BusinessRuleError):
        domain.billed_cycles(start, date(2026, 12, 1), "WEEKLY")


# ---------- Consumidores (serviço com relógio injetado) ----------

def test_primeira_fatura_vence_pela_data_utc_do_evento_e_e_idempotente():
    service = FinanceService(clock=fixed("2026-10-15T12:00:00+00:00"))
    activated = envelope("ContractActivated.v1", {"status": "ACTIVE"})
    with SessionLocal() as session:
        service.handle_contract_activated(session, activated)
        service.handle_contract_activated(session, activated)
        service.handle_contract_activated(session, {**activated, "eventId": str(uuid4())})
        session.commit()
        [invoice] = invoices(session)
        assert (invoice.kind, invoice.status, invoice.source_event_id) == ("INITIAL", "OPEN", activated["eventId"])
        assert invoice.due_date == date(2026, 10, 24)
        assert invoice.amount == Decimal("2500.00")


def test_faturamento_final_por_encerramento_e_idempotente_por_event_id():
    service = FinanceService(clock=fixed("2027-01-08T15:00:00+00:00"))
    close = closed(occurred_at="2027-01-08T15:00:00Z")
    with SessionLocal() as session:
        service.handle_contract_activated(session, envelope("ContractActivated.v1", {"status": "ACTIVE"}))
        service.handle_contract_closed(session, close)
        service.handle_contract_closed(session, close)  # reentrega do mesmo evento
        service.handle_contract_closed(session, closed(occurred_at="2027-01-09T10:00:00Z"))  # outro eventId, mesmo contrato
        session.commit()
        [final] = invoices(session, "FINAL")
        assert final.amount == Decimal("7500.00")
        assert final.source_event_id == close["eventId"]
        assert final.due_date == date(2027, 1, 18)
        assert final.status == "OPEN"
        assert len(invoices(session)) == 2


def test_faturamento_final_sem_valor_restante_nao_cria_fatura():
    service = FinanceService()
    with SessionLocal() as session:
        service.handle_contract_activated(session, envelope("ContractActivated.v1", {"status": "ACTIVE"}, cycle="ONCE"))
        service.handle_contract_closed(session, closed(cycle="ONCE"))
        session.commit()
        assert len(invoices(session)) == 1


def test_encerramento_sem_valor_restante_e_idempotente_por_event_id_fora_da_inbox():
    service = FinanceService()
    close = closed(cycle="ONCE")
    with SessionLocal() as session:
        service.handle_contract_activated(session, envelope("ContractActivated.v1", {"status": "ACTIVE"}, cycle="ONCE"))
        service.handle_contract_closed(session, close)
        session.commit()
        service.handle_contract_closed(session, close)  # reentrega sem passar pela inbox
        session.commit()
        audits = session.execute(text("SELECT result FROM integration_audit WHERE operation = 'create_final_invoice'")).scalars().all()
        assert audits == ["not_required"]
        assert len(invoices(session)) == 1


def test_primeira_fatura_cancelada_nao_e_recobrada_no_encerramento():
    service = FinanceService()
    with SessionLocal() as session:
        service.handle_contract_activated(session, envelope("ContractActivated.v1", {"status": "ACTIVE"}))
        session.commit()
        initial = invoices(session, "INITIAL")[0]
        service.cancel(session, initial.invoice_id, "Abono negociado", "corr-cancel")
        service.handle_contract_closed(session, closed())
        session.commit()
        [final] = invoices(session, "FINAL")
        assert final.amount == Decimal("7500.00")  # 4 ciclos - 2500 da fatura cancelada (cancelamento é definitivo)


def test_faturamento_final_sem_primeira_fatura_falha_sem_efeito():
    with SessionLocal() as session:
        with pytest.raises(BusinessRuleError, match="aguarda a primeira fatura"):
            FinanceService().handle_contract_closed(session, closed())
        assert invoices(session) == []


def test_verificacao_de_vencimento_e_deterministica_idempotente_e_auditavel():
    with SessionLocal() as session:
        due = date(2026, 10, 24)
        session.add_all([
            Invoice(invoice_id="00000000-0000-4000-8000-000000000001", contract_id="c1", customer_id=CUSTOMER_ID, amount=Decimal("100"), currency="BRL", due_date=due, status="OPEN"),
            Invoice(invoice_id="00000000-0000-4000-8000-000000000002", contract_id="c2", customer_id=CUSTOMER_ID, amount=Decimal("100"), currency="BRL", due_date=due, status="PAID"),
            Invoice(invoice_id="00000000-0000-4000-8000-000000000003", contract_id="c3", customer_id=CUSTOMER_ID, amount=Decimal("100"), currency="BRL", due_date=due, status="CANCELLED"),
            Invoice(invoice_id="00000000-0000-4000-8000-000000000004", contract_id="c4", customer_id=CUSTOMER_ID, amount=Decimal("100"), currency="BRL", due_date=date(2026, 10, 30), status="OPEN"),
        ])
        session.commit()
        on_due_date = FinanceService(clock=fixed("2026-10-24T23:59:00+00:00")).evaluate_overdue(session, None, "corr-1")
        assert on_due_date["markedOverdue"] == []
        after = FinanceService(clock=fixed("2026-10-25T00:01:00+00:00"))
        first = after.evaluate_overdue(session, None, "corr-2")
        second = after.evaluate_overdue(session, None, "corr-3")
        assert first["markedOverdue"] == ["00000000-0000-4000-8000-000000000001"]
        assert (first["asOf"], first["evaluatedAt"]) == ("2026-10-25", "2026-10-25T00:01:00Z")
        assert second["markedOverdue"] == [] and second["alreadyOverdue"] == 1
        overdue = session.get(Invoice, "00000000-0000-4000-8000-000000000001")
        assert overdue.status == "OVERDUE"
        assert after.to_dict(session, overdue)["overdueSince"] == "2026-10-25T00:01:00Z"
        assert {session.get(Invoice, f"00000000-0000-4000-8000-00000000000{n}").status for n in (2, 3, 4)} == {"PAID", "CANCELLED", "OPEN"}
        marks = session.execute(text("SELECT correlation_id FROM integration_audit WHERE operation = 'mark_invoice_overdue'")).scalars().all()
        assert marks == ["corr-2"]


# ---------- API ----------

@pytest.fixture
def billed_contract(client, admin_headers, integrated_contract):
    _, contract = integrated_contract
    client.post(f"/api/v1/contracts/{contract['contractId']}/activate", headers={**admin_headers, "Idempotency-Key": "t12-activate"})
    assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json() == {"processed": 1, "failed": 0}
    [invoice] = client.get("/api/v1/finance/invoices", headers=admin_headers, params={"contractId": contract["contractId"]}).json()
    return contract, invoice


@pytest.fixture
def clock_override():
    def install(moment: str):
        app.dependency_overrides[finance_service] = lambda: FinanceService(clock=fixed(moment))
    yield install
    app.dependency_overrides.pop(finance_service, None)


def pay(client, headers, invoice_id, amount, reference, key=None, currency="BRL"):
    extra = {"Idempotency-Key": key} if key else {}
    return client.post(f"/api/v1/finance/invoices/{invoice_id}/payments", headers={**headers, **extra},
                       json={"amount": amount, "currency": currency, "reference": reference})


def test_ciclo_completo_pagamento_parcial_inadimplencia_e_quitacao(client, admin_headers, billed_contract, clock_override):
    _, invoice = billed_contract
    invoice_id = invoice["invoiceId"]
    assert (invoice["kind"], invoice["status"], invoice["balance"], invoice["delinquent"]) == ("INITIAL", "OPEN", 2500.0, False)
    assert invoice["sourceEventId"] and invoice["overdueSince"] is None

    partial = pay(client, admin_headers, invoice_id, 1000, "T12-PARCIAL", key="t12-pay-1")
    assert partial.status_code == 201 and partial.headers["Idempotency-Replayed"] == "false"
    assert (partial.json()["invoice"]["status"], partial.json()["invoice"]["balance"]) == ("PARTIALLY_PAID", 1500.0)
    replay = pay(client, admin_headers, invoice_id, 1000, "T12-PARCIAL", key="t12-pay-1")
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert replay.json() == partial.json()
    assert_problem(pay(client, admin_headers, invoice_id, 999, "T12-PARCIAL-2", key="t12-pay-1"), 409, "IDEMPOTENCY_CONFLICT")
    assert len(client.get("/api/v1/finance/payments", headers=admin_headers, params={"invoiceId": invoice_id}).json()) == 1

    due = date.fromisoformat(invoice["dueDate"])
    clock_override(f"{due.isoformat()}T23:59:00+00:00")
    assert client.post("/api/v1/finance/invoices/overdue-check", headers=admin_headers).json()["markedOverdue"] == []
    clock_override(f"{(due + timedelta(days=1)).isoformat()}T00:30:00+00:00")
    before = client.get(f"/api/v1/finance/invoices/{invoice_id}", headers=admin_headers).json()
    assert (before["status"], before["delinquent"]) == ("OVERDUE", False)  # vencida calculada, ainda não registrada
    check = client.post("/api/v1/finance/invoices/overdue-check", headers=admin_headers)
    assert check.status_code == 200 and check.json()["markedOverdue"] == [invoice_id]
    assert client.post("/api/v1/finance/invoices/overdue-check", headers=admin_headers).json()["markedOverdue"] == []
    delinquent = client.get(f"/api/v1/finance/invoices/{invoice_id}", headers=admin_headers).json()
    assert (delinquent["status"], delinquent["delinquent"], delinquent["balance"]) == ("OVERDUE", True, 1500.0)
    assert delinquent["overdueSince"].endswith("Z")

    still = pay(client, admin_headers, invoice_id, 500, "T12-ATRASO-1", key="t12-pay-2").json()["invoice"]
    assert (still["status"], still["delinquent"], still["balance"]) == ("OVERDUE", True, 1000.0)
    settled = pay(client, admin_headers, invoice_id, 1000, "T12-QUITACAO", key="t12-pay-3").json()["invoice"]
    assert (settled["status"], settled["delinquent"], settled["balance"]) == ("PAID", False, 0.0)
    assert settled["overdueSince"] == delinquent["overdueSince"]
    assert assert_problem(pay(client, admin_headers, invoice_id, 1, "T12-DEPOIS"), 409, "CONFLICT")["detail"] == "Fatura já quitada"

    trail = client.get(f"/api/v1/operations/{admin_headers['X-Correlation-ID']}", headers=admin_headers).json()
    operations = [entry["operation"] for entry in trail["audit"] if entry["module"] == "finance"]
    assert operations.count("record_simulated_payment") == 3
    assert "mark_invoice_overdue" in operations and "evaluate_overdue" in operations
    assert all("reference" not in entry["details"] for entry in trail["audit"])


def test_validacoes_do_pagamento_simulado(client, admin_headers, billed_contract):
    _, invoice = billed_contract
    invoice_id = invoice["invoiceId"]
    for amount in (0, -10, 10.001):
        assert_problem(pay(client, admin_headers, invoice_id, amount, f"T12-INV-{amount}"), 422, "VALIDATION_ERROR")
    assert_problem(pay(client, admin_headers, invoice_id, 10, "T12-MOEDA-MIN", currency="brl"), 422, "VALIDATION_ERROR")
    # Códigos da v1 preservados: moeda diferente continua VALIDATION_ERROR com detalhe textual.
    assert assert_problem(pay(client, admin_headers, invoice_id, 10, "T12-MOEDA", currency="USD"), 422, "VALIDATION_ERROR")["detail"] == "Moeda diferente da fatura"
    assert_problem(pay(client, admin_headers, invoice_id, 2500.01, "T12-EXCESSO"), 409, "CONFLICT")
    assert pay(client, admin_headers, invoice_id, 100, "T12-REF").status_code == 201
    repeated = pay(client, admin_headers, invoice_id, 100, "T12-REF")
    assert repeated.status_code == 201 and repeated.headers["Idempotency-Replayed"] == "true"
    assert_problem(pay(client, admin_headers, invoice_id, 200, "T12-REF"), 409, "CONFLICT")
    missing = f"/api/v1/finance/invoices/{uuid4()}/payments"
    assert_problem(client.post(missing, headers=admin_headers, json={"amount": 1, "currency": "BRL", "reference": "T12-X"}), 404, "NOT_FOUND")
    assert client.get(f"/api/v1/finance/invoices/{invoice_id}", headers=admin_headers).json()["balance"] == 2400.0


def test_cancelamento_da_fatura(client, admin_headers, billed_contract):
    _, invoice = billed_contract
    path = f"/api/v1/finance/invoices/{invoice['invoiceId']}/cancel"
    cancelled = client.post(path, headers=admin_headers, json={"reason": "Emitida em duplicidade"})
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"
    assert client.post(path, headers=admin_headers, json={"reason": "Repetição"}).json()["status"] == "CANCELLED"
    assert_problem(pay(client, admin_headers, invoice["invoiceId"], 10, "T12-CANCELADA"), 409, "INVALID_STATE")
    assert_problem(client.post(path, headers=admin_headers, json={"reason": "x"}), 422, "VALIDATION_ERROR")


def test_fatura_com_pagamento_nao_e_cancelada(client, admin_headers, billed_contract):
    _, invoice = billed_contract
    pay(client, admin_headers, invoice["invoiceId"], 10, "T12-ANTES-CANCELAR")
    response = client.post(f"/api/v1/finance/invoices/{invoice['invoiceId']}/cancel", headers=admin_headers, json={"reason": "Tentativa"})
    assert_problem(response, 409, "INVALID_STATE")


def test_data_de_referencia_futura_exige_simulacao(client, admin_headers, billed_contract, monkeypatch):
    _, invoice = billed_contract
    after_due = (date.fromisoformat(invoice["dueDate"]) + timedelta(days=1)).isoformat()
    path = "/api/v1/finance/invoices/overdue-check"
    assert_problem(client.post(path, headers=admin_headers, json={"asOf": after_due}), 422, "BUSINESS_RULE_VIOLATION")
    assert client.post(path, headers=admin_headers, json={"asOf": "2026-01-01"}).json()["markedOverdue"] == []
    monkeypatch.setattr(settings, "finance_allow_future_as_of", True)
    simulated = client.post(path, headers=admin_headers, json={"asOf": after_due}).json()
    assert simulated == {**simulated, "asOf": after_due, "markedOverdue": [invoice["invoiceId"]]}


@pytest.mark.parametrize("method,path,allowed,denied", [
    ("post", "/api/v1/finance/invoices/overdue-check", {"finance", "operations"}, {"commercial", "contracts", "support"}),
    ("get", "/api/v1/finance/invoices", {"finance", "operations"}, {"commercial", "contracts", "support"}),
])
def test_matriz_de_autorizacao_do_financeiro(client, method, path, allowed, denied):
    for role in allowed:
        assert getattr(client, method)(path, headers={"Authorization": f"Bearer demo-{role}"}).status_code == 200, role
    for role in denied:
        assert getattr(client, method)(path, headers={"Authorization": f"Bearer demo-{role}"}).status_code == 403, role


def test_pagamento_e_cancelamento_exigem_papel_financeiro(client, billed_contract):
    _, invoice = billed_contract
    for role in ("operations", "support", "commercial"):
        headers = {"Authorization": f"Bearer demo-{role}"}
        assert pay(client, headers, invoice["invoiceId"], 10, f"T12-{role}").status_code == 403
        assert client.post(f"/api/v1/finance/invoices/{invoice['invoiceId']}/cancel", headers=headers, json={"reason": "Sem papel"}).status_code == 403
    assert pay(client, {"Authorization": "Bearer demo-finance"}, invoice["invoiceId"], 10, "T12-finance").status_code == 201


def test_encerramento_gera_fatura_final_sem_duplicar_na_reentrega(client, admin_headers, billed_contract):
    contract, _ = billed_contract
    closing = client.post(f"/api/v1/contracts/{contract['contractId']}/close", headers=admin_headers,
                          json={"endsOn": "2027-01-08", "reason": "Devolução do veículo"})
    assert closing.status_code == 200
    assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json() == {"processed": 1, "failed": 0}
    event_id = closing.json()["eventId"]
    final = [i for i in client.get("/api/v1/finance/invoices", headers=admin_headers).json() if i["kind"] == "FINAL"]
    assert len(final) == 1
    assert (final[0]["amount"], final[0]["sourceEventId"], final[0]["status"]) == (7500.0, event_id, "OPEN")

    with SessionLocal() as session:  # reentrega pelo despachante: a inbox descarta
        session.get(OutboxEvent, event_id).status = "PENDING"
        session.commit()
    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    with SessionLocal() as session:  # inbox perdida: a unicidade por eventId e por contrato ainda protege
        session.query(InboxEvent).filter_by(event_id=event_id, consumer="finance-faturamento-final").delete()
        session.get(OutboxEvent, event_id).status = "PENDING"
        session.commit()
    assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json()["failed"] == 0
    with SessionLocal() as session:
        assert len(invoices(session, "FINAL")) == 1
        assert len(invoices(session, "INITIAL")) == 1
        assert session.query(InboxEvent).filter_by(event_id=event_id, consumer="finance-faturamento-final").count() == 1


def test_simulacao_de_data_futura_nao_inicia_com_demo_publica(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(settings, "public_demo", True)
    monkeypatch.setattr(settings, "demo_access_token", "segredo-aleatorio-de-teste-0123456789")
    monkeypatch.setattr(settings, "finance_allow_future_as_of", True)
    with pytest.raises(RuntimeError, match="FINANCE_ALLOW_FUTURE_AS_OF"):
        with TestClient(app):
            pass
    monkeypatch.setattr(settings, "finance_allow_future_as_of", False)
    with TestClient(app) as started:
        assert started.get("/health/live").status_code == 200


def test_servico_recusa_data_futura_na_demo_publica_mesmo_com_a_flag(monkeypatch):
    monkeypatch.setattr(settings, "public_demo", True)
    monkeypatch.setattr(settings, "finance_allow_future_as_of", True)
    with SessionLocal() as session, pytest.raises(BusinessRuleError):
        FinanceService(clock=fixed("2026-10-14T12:00:00+00:00")).evaluate_overdue(session, date(2026, 10, 30), "corr")


# ---------- Migração ----------

def test_migracao_0004_preserva_faturas_antigas(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'financeiro.db'}")
    with engine.begin() as connection:
        command.upgrade(alembic_config(connection), "0003_contract_closing")
        connection.execute(text(
            "INSERT INTO finance_invoices (invoice_id, contract_id, customer_id, amount, currency, due_date, status) VALUES "
            "('i1', 'c1', 'cu', 100, 'BRL', '2026-10-01', 'OPEN'), ('i2', 'c2', 'cu', 100, 'BRL', '2026-10-01', 'OPEN'), "
            "('i3', 'c3', 'cu', 100, 'BRL', '2026-10-01', 'PAID')"))
        connection.execute(text("INSERT INTO finance_payments (payment_id, invoice_id, amount, currency, reference) VALUES ('p1', 'i2', 40, 'BRL', 'R1')"))
    with engine.begin() as connection:
        command.upgrade(alembic_config(connection), "head")
    with engine.connect() as connection:
        rows = dict(connection.execute(text("SELECT invoice_id, status || ':' || kind FROM finance_invoices")).all())
        uniques = {constraint["name"] for constraint in inspect(connection).get_unique_constraints("finance_invoices")}
    assert rows == {"i1": "OPEN:INITIAL", "i2": "PARTIALLY_PAID:INITIAL", "i3": "PAID:INITIAL"}
    assert uniques == {"uq_invoice_contract_kind", "uq_invoice_source_event"}
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO finance_invoices (invoice_id, contract_id, customer_id, amount, currency, due_date, status, kind) "
                                "VALUES ('i4', 'c1', 'cu', 50, 'BRL', '2026-11-01', 'OPEN', 'FINAL')"))
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text("INSERT INTO finance_invoices (invoice_id, contract_id, customer_id, amount, currency, due_date, status) "
                                "VALUES ('i5', 'c1', 'cu', 50, 'BRL', '2026-11-01', 'OPEN')"))


def test_migracao_0004_gera_sql_postgresql():
    config = alembic_config()
    config.set_main_option("sqlalchemy.url", "postgresql+psycopg://migracao@localhost/archcorp")
    config.output_buffer = StringIO()
    command.upgrade(config, "0003_contract_closing:0004_finance_lifecycle", sql=True)
    sql = config.output_buffer.getvalue()
    assert "ALTER TABLE finance_invoices ADD COLUMN kind VARCHAR(20) DEFAULT 'INITIAL' NOT NULL" in sql
    assert "ADD CONSTRAINT uq_invoice_contract_kind UNIQUE (contract_id, kind)" in sql
    assert "DROP CONSTRAINT uq_invoice_contract;" in sql


def migrated_database(tmp_path, name: str):
    engine = create_engine(f"sqlite:///{tmp_path / name}")
    with engine.begin() as connection:
        command.upgrade(alembic_config(connection), "head")
        connection.execute(text(
            "INSERT INTO finance_invoices (invoice_id, contract_id, customer_id, amount, currency, due_date, status, kind) VALUES "
            "('i1', 'c1', 'cu', 100, 'BRL', '2026-10-01', 'PARTIALLY_PAID', 'INITIAL'), "
            "('i2', 'c2', 'cu', 100, 'BRL', '2026-10-01', 'OVERDUE', 'INITIAL'), "
            "('i3', 'c3', 'cu', 100, 'BRL', '2026-10-01', 'CANCELLED', 'INITIAL'), "
            "('i4', 'c4', 'cu', 100, 'BRL', '2026-10-01', 'PAID', 'INITIAL')"))
    return engine


def test_downgrade_0004_sem_fatura_final_restaura_a_0003(tmp_path):
    engine = migrated_database(tmp_path, "downgrade.db")
    with engine.begin() as connection:
        command.downgrade(alembic_config(connection), "0003_contract_closing")
    with engine.connect() as connection:
        rows = dict(connection.execute(text("SELECT invoice_id, status FROM finance_invoices")).all())
        columns = {column["name"] for column in inspect(connection).get_columns("finance_invoices")}
        uniques = {constraint["name"] for constraint in inspect(connection).get_unique_constraints("finance_invoices")}
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
    # PARTIALLY_PAID e OVERDUE voltam a OPEN; CANCELLED não tem equivalente e permanece (documentado na migração).
    assert rows == {"i1": "OPEN", "i2": "OPEN", "i3": "CANCELLED", "i4": "PAID"}
    assert not {"kind", "source_event_id", "overdue_since"} & columns
    assert uniques == {"uq_invoice_contract"}
    assert revision == "0003_contract_closing"


def test_downgrade_0004_com_fatura_final_e_bloqueado_sem_alterar_dados(tmp_path):
    engine = migrated_database(tmp_path, "downgrade-final.db")
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO finance_invoices (invoice_id, contract_id, customer_id, amount, currency, due_date, status, kind) "
                                "VALUES ('f1', 'c1', 'cu', 50, 'BRL', '2026-11-01', 'OPEN', 'FINAL')"))
    with pytest.raises(RuntimeError, match="1 fatura\\(s\\) FINAL"), engine.begin() as connection:
        command.downgrade(alembic_config(connection), "0003_contract_closing")
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
        statuses = dict(connection.execute(text("SELECT invoice_id, status FROM finance_invoices")).all())
    assert revision == "0004_finance_lifecycle"
    assert statuses["i1"] == "PARTIALLY_PAID" and statuses["f1"] == "OPEN"
