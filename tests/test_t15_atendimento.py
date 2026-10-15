"""T15 · Atendimento: abertura, SLA, responsável, resolução e reconciliação.

Complementa `test_f3_abre_chamado_com_sla_e_inicia_resolucao` e
`test_indisponibilidade_de_contratos_cria_estado_pendente` com a máquina de
estados única, o SLA calculado com relógio injetável, o histórico de
responsável, a resolução idempotente e a reconciliação explícita (individual
e em lote) dos chamados `PENDING_ENTITLEMENT`.
"""
import io
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from alembic import command
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from archcorp import main
from archcorp.config import settings
from archcorp.contracts.public import ContractsUnavailableError
from archcorp.exceptions import InvalidStateError
from archcorp.infrastructure.db import SessionLocal
from archcorp.infrastructure.migrate import alembic_config
from archcorp.integration.models import AuditLog, IdempotencyRecord, InboxEvent, OutboxEvent
from archcorp.observability import JsonFormatter
from archcorp.support import domain
from archcorp.support.domain import TICKET_TRANSITIONS, Priority, SlaStatus, TicketStatus
from archcorp.support.models import Ticket, TicketHistory
from archcorp.support.service import TicketService
from archcorp.workflow.models import ProcessInstance

T0 = datetime(2026, 10, 20, 9, 0, tzinfo=timezone.utc)
CORRELATION = "22222222-2222-4222-8222-222222222222"
DESCRIPTION = "Veículo não liga no pátio de retirada (cenário fictício)"
PROBLEM_FIELDS = {"type", "title", "status", "detail", "instance", "code", "correlationId"}


class FakeClock:
    def __init__(self, start: datetime):
        self.current = start

    def __call__(self) -> datetime:
        return self.current

    def advance(self, **delta) -> None:
        self.current += timedelta(**delta)


class FakeEntitlementPort:
    """Simulador da porta pública de Contracts para testes do serviço sem HTTP."""

    def __init__(self, result: dict | None = None, error: Exception | None = None, fail_after: int | None = None, delegate=None):
        self.result, self.error, self.fail_after, self.delegate, self.calls = result, error, fail_after, delegate, 0

    def entitlement(self, session, contract_id, customer_id, service_code):
        self.calls += 1
        if self.error and (self.fail_after is None or self.calls > self.fail_after):
            raise self.error
        if self.delegate:
            return self.delegate.entitlement(session, contract_id, customer_id, service_code)
        return self.result


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock(T0)
    monkeypatch.setattr(main.tickets, "clock", fake)
    return fake


@pytest.fixture
def active_contract(client, admin_headers, integrated_contract):
    customer, contract = integrated_contract
    response = client.post(f"/api/v1/contracts/{contract['contractId']}/activate",
                           headers={**admin_headers, "Idempotency-Key": "t15-activate"})
    assert response.status_code == 200, response.text
    return customer, contract


@pytest.fixture
def json_logs():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("archcorp")
    logger.addHandler(handler)
    try:
        yield lambda: [json.loads(line) for line in stream.getvalue().splitlines() if line.startswith("{")]
    finally:
        logger.removeHandler(handler)


def contracts_available(monkeypatch, available: bool) -> None:
    monkeypatch.setattr(settings, "contract_adapter_available", available)


def body_for(customer: dict, contract: dict, **overrides) -> dict:
    return {"customerId": customer["customerId"], "contractId": contract["contractId"], "serviceCode": "RENTAL-FLEX",
            "category": "OUTAGE", "description": DESCRIPTION, **overrides}


def open_ticket(client, headers: dict, body: dict, key: str):
    return client.post("/api/v1/support/tickets", headers={**headers, "Idempotency-Key": key}, json=body)


def assert_problem(response, status: int, code: str) -> dict:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert PROBLEM_FIELDS.issubset(body)
    assert (body["status"], body["code"]) == (status, code)
    return body


def events(event_type: str) -> list[OutboxEvent]:
    with SessionLocal() as session:
        return list(session.scalars(select(OutboxEvent).where(OutboxEvent.event_type == event_type)))


def history(ticket_id: str) -> list[TicketHistory]:
    with SessionLocal() as session:
        return list(session.scalars(select(TicketHistory).where(TicketHistory.ticket_id == ticket_id).order_by(TicketHistory.id)))


def audits(operation: str) -> list[AuditLog]:
    with SessionLocal() as session:
        return list(session.scalars(select(AuditLog).where(AuditLog.operation == operation).order_by(AuditLog.id)))


def iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


# ---------- Domínio (sem HTTP nem banco) ----------

def test_maquina_de_estados_unica_do_chamado():
    assert TICKET_TRANSITIONS == {
        TicketStatus.PENDING_ENTITLEMENT: {TicketStatus.OPEN, TicketStatus.REJECTED_ENTITLEMENT},
        TicketStatus.OPEN: {TicketStatus.RESOLVED},
        TicketStatus.REJECTED_ENTITLEMENT: set(),
        TicketStatus.RESOLVED: set(),
    }
    for current in TicketStatus:
        for target in TicketStatus:
            if target in TICKET_TRANSITIONS[current]:
                domain.ensure_ticket_transition(current, target)
            else:
                with pytest.raises(InvalidStateError):
                    domain.ensure_ticket_transition(current, target)
    domain.ensure_assignable("OPEN")
    domain.ensure_assignable("PENDING_ENTITLEMENT")
    for final in ("RESOLVED", "REJECTED_ENTITLEMENT"):
        with pytest.raises(InvalidStateError):
            domain.ensure_assignable(final)


@pytest.mark.parametrize(("category", "priority"), [
    ("OUTAGE", Priority.HIGH), ("SECURITY", Priority.HIGH), ("ASSISTANCE", Priority.NORMAL), ("QUESTION", Priority.NORMAL),
])
def test_prioridade_derivada_da_categoria(category, priority):
    assert domain.priority_for(category) == priority


def test_prazo_e_estado_de_sla_sao_deterministicos_com_o_relogio():
    due = domain.due_at(T0, 8)
    assert due == T0 + timedelta(hours=8)
    assert domain.due_at(T0.replace(tzinfo=None), 8) == due  # data sem fuso do SQLite é tratada como UTC
    assert domain.sla_status("OPEN", due, due) == SlaStatus.WITHIN
    assert domain.sla_status("OPEN", due, due + timedelta(seconds=1)) == SlaStatus.BREACHED
    assert domain.sla_status("RESOLVED", due, due + timedelta(days=3), resolved_at=due) == SlaStatus.MET
    assert domain.sla_status("RESOLVED", due, due, resolved_at=due + timedelta(seconds=1)) == SlaStatus.BREACHED
    assert domain.sla_status("RESOLVED", due, due, resolved_at=None) is None  # resolvido antes da T15
    assert domain.sla_status("PENDING_ENTITLEMENT", None, due) == SlaStatus.PENDING
    assert domain.sla_status("REJECTED_ENTITLEMENT", None, due) == SlaStatus.NOT_APPLICABLE
    assert domain.iso_utc(T0.replace(tzinfo=None)) == "2026-10-20T09:00:00Z"


@pytest.mark.parametrize("description", [
    "Cliente informou CPF 123.456.789-09 no balcão", "CNPJ 12345678000190 do cliente", "Cartão 4111 1111 1111 1111 recusado",
    "Ligar para +55 31 99999-9999", "Veículo placa ABC1D23 parado", "Veículo placa ABC-1234 parado", "Contato gestor@cliente.com.br",
])
def test_descricao_com_dado_sensivel_e_detectada(description):
    assert domain.contains_sensitive_data(description)


@pytest.mark.parametrize("description", [DESCRIPTION, "Pneu furado na rodovia km 12, aguardando guincho", "SLA de 8 h para o grupo SUV"])
def test_relato_sem_dado_sensivel_e_aceito(description):
    assert not domain.contains_sensitive_data(description)


# ---------- Serviço com porta falsa de Contracts (sem HTTP) ----------

def test_servico_calcula_prazo_com_relogio_injetado_e_trata_indisponibilidade():
    data = {"customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "contractId": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            "serviceCode": "RENTAL-FLEX", "category": "QUESTION", "description": DESCRIPTION}
    clock = FakeClock(T0)
    with SessionLocal() as session:
        eligible = TicketService(FakeEntitlementPort({"eligible": True, "slaHours": 4}), clock)
        opened, replay = eligible.open(session, data, "svc-1", CORRELATION, "support")
        assert not replay
        assert (opened["status"], opened["priority"], opened["slaHours"]) == ("OPEN", "NORMAL", 4)
        assert (opened["openedAt"], opened["dueAt"], opened["slaStatus"]) == ("2026-10-20T09:00:00Z", "2026-10-20T13:00:00Z", "WITHIN")

        for error in (ContractsUnavailableError("simulado"), TimeoutError("simulado"), ConnectionError("simulado")):
            down = TicketService(FakeEntitlementPort(error=error), clock)
            pending, _ = down.open(session, data, f"svc-{type(error).__name__}", CORRELATION)
            assert (pending["status"], pending["slaHours"], pending["dueAt"], pending["slaStatus"]) == ("PENDING_ENTITLEMENT", None, None, "PENDING")


# ---------- Abertura via API ----------

def test_abertura_registra_prazo_estado_de_sla_e_historico_sem_dado_sensivel(client, admin_headers, active_contract, clock):
    customer, contract = active_contract
    response = open_ticket(client, admin_headers, body_for(customer, contract), "t15-open")
    assert response.status_code == 201, response.text
    ticket = response.json()
    assert (ticket["status"], ticket["priority"], ticket["slaHours"]) == ("OPEN", "HIGH", 8)
    assert ticket["openedAt"] == iso(T0)
    assert ticket["dueAt"] == iso(T0 + timedelta(hours=8))
    assert (ticket["slaStatus"], ticket["resolvedAt"]) == ("WITHIN", None)

    detail = client.get(f"/api/v1/support/tickets/{ticket['ticketId']}", headers=admin_headers).json()
    assert detail["dueAt"] == ticket["dueAt"] and detail["openedAt"].endswith("Z")  # ISO 8601 UTC após releitura do banco
    entries = client.get(f"/api/v1/support/tickets/{ticket['ticketId']}/history", headers=admin_headers).json()
    assert [(e["action"], e["fromStatus"], e["toStatus"], e["actorRole"], e["correlationId"]) for e in entries] == [
        ("OPENED", None, "OPEN", "admin", admin_headers["X-Correlation-ID"])]

    [event] = events("TicketOpened.v1")
    assert event.correlation_id == admin_headers["X-Correlation-ID"]
    assert event.payload["slaStatus"] == "WITHIN" and "description" not in event.payload
    [entry] = audits("open_ticket")
    assert DESCRIPTION not in json.dumps(entry.details, ensure_ascii=False)


def test_abertura_idempotente_compara_todo_o_pedido(client, admin_headers, active_contract):
    customer, contract = active_contract
    body = body_for(customer, contract)
    first = open_ticket(client, admin_headers, body, "t15-idem")
    second = open_ticket(client, admin_headers, body, "t15-idem")
    assert first.status_code == second.status_code == 201
    assert (first.headers["Idempotency-Replayed"], second.headers["Idempotency-Replayed"]) == ("false", "true")
    assert second.json()["ticketId"] == first.json()["ticketId"]

    changed = open_ticket(client, admin_headers, {**body, "description": "Outro relato da ocorrência"}, "t15-idem")
    assert_problem(changed, 409, "IDEMPOTENCY_CONFLICT")
    with SessionLocal() as session:
        assert session.query(Ticket).count() == 1
    assert len(events("TicketOpened.v1")) == 1
    assert len(history(first.json()["ticketId"])) == 1


def test_idempotencia_de_registro_anterior_a_t15_compara_campos_da_resposta(client, admin_headers, active_contract):
    customer, contract = active_contract
    body = body_for(customer, contract)
    stored = {**body, "ticketId": "dddddddd-dddd-4ddd-8ddd-dddddddddddd", "status": "OPEN", "priority": "HIGH", "slaHours": 8,
              "dueAt": "2026-10-01T18:10:00Z"}
    stored.pop("description")
    with SessionLocal() as session:
        session.add(IdempotencyRecord(key="legacy-key", operation="open_ticket", response=stored))
        session.commit()
    replay = open_ticket(client, admin_headers, body, "legacy-key")
    assert replay.status_code == 201 and replay.headers["Idempotency-Replayed"] == "true"
    assert_problem(open_ticket(client, admin_headers, {**body, "category": "QUESTION"}, "legacy-key"), 409, "IDEMPOTENCY_CONFLICT")


def test_abertura_inelegivel_nao_grava_nada_nem_consome_a_chave(client, admin_headers, integrated_contract):
    customer, contract = integrated_contract  # contrato ainda em rascunho
    body = body_for(customer, contract)
    assert_problem(open_ticket(client, admin_headers, body, "t15-draft"), 422, "BUSINESS_RULE_VIOLATION")
    with SessionLocal() as session:
        assert session.query(Ticket).count() == 0
        assert session.get(IdempotencyRecord, {"key": "t15-draft", "operation": "open_ticket"}) is None
    assert events("TicketOpened.v1") == []
    client.post(f"/api/v1/contracts/{contract['contractId']}/activate", headers={**admin_headers, "Idempotency-Key": "t15-late-activate"})
    accepted = open_ticket(client, admin_headers, body, "t15-draft")
    assert accepted.status_code == 201 and accepted.headers["Idempotency-Replayed"] == "false"


@pytest.mark.parametrize(("change", "loc"), [
    ({"category": ""}, "category"),
    ({"description": "x"}, "description"),
])
def test_validacao_na_fronteira_rejeita_sem_criar_chamado(client, admin_headers, active_contract, change, loc):
    customer, contract = active_contract
    response = open_ticket(client, admin_headers, body_for(customer, contract, **change), "t15-invalid")
    body = assert_problem(response, 422, "VALIDATION_ERROR")
    assert body["errors"][0]["loc"] == ["body", loc]
    with SessionLocal() as session:
        assert session.query(Ticket).count() == 0
        assert session.get(IdempotencyRecord, {"key": "t15-invalid", "operation": "open_ticket"}) is None


def test_falha_do_adaptador_na_abertura_vira_pendente_com_log_sem_descricao(client, admin_headers, active_contract, monkeypatch, json_logs):
    customer, contract = active_contract
    monkeypatch.setattr(main.tickets, "contracts", FakeEntitlementPort(error=TimeoutError("contracts não respondeu")))
    response = open_ticket(client, admin_headers, body_for(customer, contract), "t15-timeout")
    assert response.status_code == 201, response.text
    assert (response.json()["status"], response.json()["slaStatus"]) == ("PENDING_ENTITLEMENT", "PENDING")
    warnings = [line for line in json_logs() if line["operation"] == "support_entitlement"]
    assert warnings and warnings[0]["result"] == "unavailable" and warnings[0]["level"] == "WARNING"
    assert warnings[0]["correlationId"] == admin_headers["X-Correlation-ID"]
    assert all(DESCRIPTION not in line["message"] for line in json_logs())


# ---------- SLA ----------

def test_estado_de_sla_vence_com_o_relogio_e_fica_auditado_na_resolucao(client, admin_headers, active_contract, clock):
    customer, contract = active_contract
    late = open_ticket(client, admin_headers, body_for(customer, contract), "t15-late").json()
    on_time = open_ticket(client, admin_headers, body_for(customer, contract, category="QUESTION"), "t15-on-time").json()
    path = f"/api/v1/support/tickets/{late['ticketId']}"

    clock.advance(hours=8)
    assert client.get(path, headers=admin_headers).json()["slaStatus"] == "WITHIN"
    met = client.post(f"/api/v1/support/tickets/{on_time['ticketId']}/resolve", headers=admin_headers).json()
    assert (met["status"], met["slaStatus"], met["resolvedAt"]) == ("RESOLVED", "MET", iso(T0 + timedelta(hours=8)))

    clock.advance(seconds=1)
    assert client.get(path, headers=admin_headers).json()["slaStatus"] == "BREACHED"
    listed = {t["ticketId"]: t["slaStatus"] for t in client.get("/api/v1/support/tickets", headers=admin_headers).json()}
    assert listed == {late["ticketId"]: "BREACHED", on_time["ticketId"]: "MET"}

    breached = client.post(f"{path}/resolve", headers=admin_headers).json()
    assert (breached["slaStatus"], breached["resolvedAt"]) == ("BREACHED", iso(T0 + timedelta(hours=8, seconds=1)))
    clock.advance(days=30)
    assert client.get(path, headers=admin_headers).json()["slaStatus"] == "BREACHED"  # fixado na resolução
    assert history(late["ticketId"])[-1].sla_status == "BREACHED"
    resolved_audit = {a.entity_id: a.details["slaStatus"] for a in audits("resolve_ticket")}
    assert resolved_audit == {late["ticketId"]: "BREACHED", on_time["ticketId"]: "MET"}
    assert {e.payload["ticketId"]: e.payload["slaStatus"] for e in events("TicketResolved.v1")} == resolved_audit


# ---------- Responsável ----------

def test_atribuicao_e_reatribuicao_com_historico_auditoria_e_papel(client, admin_headers, active_contract):
    customer, contract = active_contract
    ticket = open_ticket(client, admin_headers, body_for(customer, contract), "t15-assign").json()
    path = f"/api/v1/support/tickets/{ticket['ticketId']}"
    support = {"Authorization": "Bearer demo-support", "X-Correlation-ID": CORRELATION}

    assert client.post(f"{path}/assign", headers=support, json={"owner": "  Equipe de assistência  "}).json()["owner"] == "Equipe de assistência"
    assert client.post(f"{path}/assign", headers=support, json={"owner": "Equipe de assistência"}).status_code == 200  # sem mudança
    assert client.post(f"{path}/assign", headers=admin_headers, json={"owner": "Equipe de pátio"}).json()["owner"] == "Equipe de pátio"

    entries = client.get(f"{path}/history", headers=support).json()
    assert [(e["action"], e["owner"], e["previousOwner"], e["actorRole"], e["correlationId"]) for e in entries[1:]] == [
        ("ASSIGNED", "Equipe de assistência", None, "support", CORRELATION),
        ("REASSIGNED", "Equipe de pátio", "Equipe de assistência", "admin", admin_headers["X-Correlation-ID"]),
    ]
    assert [(a.details["action"], a.details["owner"], a.details["previousOwner"]) for a in audits("assign_ticket")] == [
        ("ASSIGNED", "Equipe de assistência", None), ("REASSIGNED", "Equipe de pátio", "Equipe de assistência")]
    assert all("demo-" not in json.dumps(a.details) for a in audits("assign_ticket"))  # papel, nunca o token

    client.post(f"{path}/resolve", headers=admin_headers)
    assert_problem(client.post(f"{path}/assign", headers=admin_headers, json={"owner": "Equipe de pátio"}), 409, "CONFLICT")
    assert entries[-1]["action"] == "REASSIGNED" and history(ticket["ticketId"])[-1].owner == "Equipe de pátio"


# ---------- Resolução ----------

def test_resolucao_idempotente_publica_um_evento(client, admin_headers, active_contract):
    customer, contract = active_contract
    ticket = open_ticket(client, admin_headers, body_for(customer, contract), "t15-resolve").json()
    path = f"/api/v1/support/tickets/{ticket['ticketId']}/resolve"
    headers = {**admin_headers, "Idempotency-Key": "resolve-command"}
    first = client.post(path, headers=headers)
    second = client.post(path, headers=headers)
    assert first.status_code == second.status_code == 200
    assert (first.headers["Idempotency-Replayed"], second.headers["Idempotency-Replayed"]) == ("false", "true")
    assert second.json() == first.json()
    assert len(events("TicketResolved.v1")) == 1
    assert [e.action for e in history(ticket["ticketId"])] == ["OPENED", "RESOLVED"]
    assert len(audits("resolve_ticket")) == 1


def test_resolucao_exige_chamado_aberto(client, admin_headers, active_contract, monkeypatch):
    customer, contract = active_contract
    contracts_available(monkeypatch, False)
    pending = open_ticket(client, admin_headers, body_for(customer, contract), "t15-pending-resolve").json()
    body = assert_problem(client.post(f"/api/v1/support/tickets/{pending['ticketId']}/resolve", headers=admin_headers), 409, "CONFLICT")
    assert body["detail"] == "Somente chamado aberto pode ser resolvido"
    assert events("TicketResolved.v1") == []


# ---------- Reconciliação ----------

def test_reconciliacao_com_contracts_ainda_indisponivel_retorna_503_sem_efeito(client, admin_headers, active_contract, monkeypatch):
    customer, contract = active_contract
    contracts_available(monkeypatch, False)
    pending = open_ticket(client, admin_headers, body_for(customer, contract), "t15-still-down").json()
    response = client.post(f"/api/v1/support/tickets/{pending['ticketId']}/reconcile", headers=admin_headers)
    assert_problem(response, 503, "SERVICE_UNAVAILABLE")
    assert client.get(f"/api/v1/support/tickets/{pending['ticketId']}", headers=admin_headers).json()["status"] == "PENDING_ENTITLEMENT"
    assert events("TicketEntitlementReconciled.v1") == []
    assert [a.result for a in audits("reconcile_entitlement")] == ["unavailable"]


def test_reconciliacao_conta_o_prazo_da_abertura_e_e_idempotente(client, admin_headers, active_contract, monkeypatch, clock):
    customer, contract = active_contract
    contracts_available(monkeypatch, False)
    pending = open_ticket(client, admin_headers, body_for(customer, contract, category="QUESTION"), "t15-reconcile").json()
    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    clock.advance(hours=3)
    contracts_available(monkeypatch, True)

    path = f"/api/v1/support/tickets/{pending['ticketId']}/reconcile"
    headers = {**admin_headers, "X-Correlation-ID": CORRELATION, "Idempotency-Key": "reconcile-command"}
    first = client.post(path, headers=headers)
    second = client.post(path, headers={**headers, "X-Correlation-ID": admin_headers["X-Correlation-ID"]})
    assert first.status_code == second.status_code == 200
    assert (first.headers["Idempotency-Replayed"], second.headers["Idempotency-Replayed"]) == ("false", "true")
    reconciled = first.json()
    assert (reconciled["status"], reconciled["slaHours"], reconciled["slaStatus"]) == ("OPEN", 8, "WITHIN")
    assert reconciled["dueAt"] == iso(T0 + timedelta(hours=8))  # o tempo de indisponibilidade não estende o SLA
    assert second.json() == reconciled

    [event] = events("TicketEntitlementReconciled.v1")
    assert event.correlation_id == CORRELATION and event.payload["dueAt"] == reconciled["dueAt"]
    [entry] = [e for e in history(pending["ticketId"]) if e.action == "ENTITLEMENT_CONFIRMED"]
    assert (entry.from_status, entry.to_status, entry.correlation_id) == ("PENDING_ENTITLEMENT", "OPEN", CORRELATION)
    trace = client.get(f"/api/v1/operations/{CORRELATION}", headers=admin_headers).json()
    assert [a["operation"] for a in trace["audit"]] == ["reconcile_entitlement"]
    assert [e["eventType"] for e in trace["events"]] == ["TicketEntitlementReconciled.v1"]

    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    with SessionLocal() as session:
        process = session.scalar(select(ProcessInstance).where(ProcessInstance.reference_id == pending["ticketId"]))
        assert domain.iso_utc(process.due_at) == reconciled["dueAt"]


def test_reconciliacao_rejeita_quando_o_contrato_deixa_de_ser_elegivel(client, admin_headers, active_contract, monkeypatch):
    customer, contract = active_contract
    contracts_available(monkeypatch, False)
    pending = open_ticket(client, admin_headers, body_for(customer, contract), "t15-reject").json()
    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    assert client.post(f"/api/v1/contracts/{contract['contractId']}/close", headers=admin_headers, json={"reason": "Fim do teste"}).status_code == 200
    contracts_available(monkeypatch, True)

    rejected = client.post(f"/api/v1/support/tickets/{pending['ticketId']}/reconcile", headers=admin_headers).json()
    assert (rejected["status"], rejected["slaHours"], rejected["dueAt"], rejected["slaStatus"]) == ("REJECTED_ENTITLEMENT", None, None, "NOT_APPLICABLE")
    assert_problem(client.post(f"/api/v1/support/tickets/{pending['ticketId']}/resolve", headers=admin_headers), 409, "CONFLICT")
    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    with SessionLocal() as session:
        process = session.scalar(select(ProcessInstance).where(ProcessInstance.reference_id == pending["ticketId"]))
        assert process.state == "CANCELLED"
    assert [a.result for a in audits("reconcile_entitlement")] == ["rejected"]


def test_reconciliacao_em_lote_e_explicita_idempotente_e_auditavel(client, admin_headers, active_contract, monkeypatch):
    customer, contract = active_contract
    contracts_available(monkeypatch, False)
    for key, service in (("t15-batch-1", "RENTAL-FLEX"), ("t15-batch-2", "RENTAL-FLEX"), ("t15-batch-3", "OTHER-SERVICE")):
        assert open_ticket(client, admin_headers, body_for(customer, contract, serviceCode=service), key).json()["status"] == "PENDING_ENTITLEMENT"
    operations = {"Authorization": "Bearer demo-operations", "X-Correlation-ID": CORRELATION}

    assert_problem(client.post("/api/v1/support/tickets/reconcile-pending", headers=operations), 503, "SERVICE_UNAVAILABLE")
    assert events("TicketEntitlementReconciled.v1") == []

    contracts_available(monkeypatch, True)
    summary = client.post("/api/v1/support/tickets/reconcile-pending", headers=operations).json()
    assert (summary["confirmed"], summary["rejected"], summary["remaining"], summary["contractsAvailable"]) == (2, 1, 0, True)
    assert sorted(t["status"] for t in summary["tickets"]) == ["OPEN", "OPEN", "REJECTED_ENTITLEMENT"]

    again = client.post("/api/v1/support/tickets/reconcile-pending", headers=operations).json()
    assert again == {"confirmed": 0, "rejected": 0, "remaining": 0, "contractsAvailable": True, "tickets": []}
    assert len(events("TicketEntitlementReconciled.v1")) == 3
    assert [(a.result, a.details["confirmed"], a.details["actorRole"]) for a in audits("reconcile_pending")] == [
        ("interrupted", 0, "operations"), ("success", 2, "operations"), ("success", 0, "operations")]
    assert {e.actor_role for t in summary["tickets"] for e in history(t["ticketId"]) if e.action.startswith("ENTITLEMENT")} == {"operations"}


def test_reconciliacao_em_lote_interrompida_preserva_o_que_foi_confirmado(client, admin_headers, active_contract, monkeypatch, clock):
    customer, contract = active_contract
    contracts_available(monkeypatch, False)
    for index in range(2):
        open_ticket(client, admin_headers, body_for(customer, contract), f"t15-partial-{index}")
        clock.advance(minutes=1)
    contracts_available(monkeypatch, True)
    monkeypatch.setattr(main.tickets, "contracts", FakeEntitlementPort(error=ContractsUnavailableError("queda"), fail_after=1, delegate=main.contracts))

    partial = client.post("/api/v1/support/tickets/reconcile-pending", headers=admin_headers).json()
    assert (partial["confirmed"], partial["remaining"], partial["contractsAvailable"]) == (1, 1, False)
    monkeypatch.setattr(main.tickets, "contracts", main.contracts)
    rest = client.post("/api/v1/support/tickets/reconcile-pending", headers=admin_headers).json()
    assert (rest["confirmed"], rest["remaining"], rest["contractsAvailable"]) == (1, 0, True)
    assert len(events("TicketEntitlementReconciled.v1")) == 2


# ---------- Eventos: envelope, correlação e reentrega ----------

def test_reentrega_dos_eventos_do_chamado_nao_duplica_efeitos(client, admin_headers, active_contract):
    customer, contract = active_contract
    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    ticket = open_ticket(client, admin_headers, body_for(customer, contract), "t15-redelivery").json()
    client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers)
    client.post(f"/api/v1/support/tickets/{ticket['ticketId']}/resolve", headers=admin_headers)
    assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json() == {"processed": 1, "failed": 0}
    with SessionLocal() as session:
        inbox_before = session.query(InboxEvent).count()
        for event in session.scalars(select(OutboxEvent).where(OutboxEvent.producer == "support")):
            event.status = "PENDING"  # simula reentrega do broker
        session.commit()
    assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json() == {"processed": 2, "failed": 0}
    with SessionLocal() as session:
        processes = session.scalars(select(ProcessInstance).where(ProcessInstance.reference_id == ticket["ticketId"])).all()
        assert [(p.process_type, p.state) for p in processes] == [("TICKET_RESOLUTION", "COMPLETED")]
        assert session.query(InboxEvent).count() == inbox_before
    assert len(audits("start_ticket_resolution")) == len(audits("complete_ticket_resolution")) == 1


def test_envelopes_dos_eventos_do_chamado_validam_contra_asyncapi(client, admin_headers, active_contract, monkeypatch):
    customer, contract = active_contract
    contracts_available(monkeypatch, False)
    pending = open_ticket(client, admin_headers, body_for(customer, contract), "t15-envelope").json()
    contracts_available(monkeypatch, True)
    client.post(f"/api/v1/support/tickets/{pending['ticketId']}/reconcile", headers=admin_headers)
    client.post(f"/api/v1/support/tickets/{pending['ticketId']}/resolve", headers=admin_headers)

    document = yaml.safe_load(Path("docs/events/asyncapi.yaml").read_text(encoding="utf-8"))
    registry = Registry().with_resource("urn:t15", Resource(contents=document, specification=DRAFT202012))
    messages = {m["name"]: key for key, m in document["components"]["messages"].items()}
    with SessionLocal() as session:
        envelopes = [e.envelope() for e in session.scalars(select(OutboxEvent).where(OutboxEvent.producer == "support"))]
    assert [e["eventType"] for e in envelopes] == ["TicketOpened.v1", "TicketEntitlementReconciled.v1", "TicketResolved.v1"]
    for envelope in envelopes:
        validator = Draft202012Validator({"$ref": f"urn:t15#/components/messages/{messages[envelope['eventType']]}/payload"}, registry=registry)
        assert [error.message for error in validator.iter_errors(envelope)] == []
        assert envelope["occurredAt"].endswith("Z") and envelope["payload"]["openedAt"].endswith("Z")
        assert envelope["correlationId"] == admin_headers["X-Correlation-ID"]
        assert "description" not in envelope["payload"]


# ---------- Autorização ----------

SUPPORT_ROUTES = [
    ("post", "/api/v1/support/tickets", {"support"}, {"commercial", "contracts", "finance", "operations"}),
    ("get", "/api/v1/support/tickets", {"support", "operations"}, {"commercial", "contracts", "finance"}),
    ("get", "/api/v1/support/tickets/{ticket}", {"support", "operations"}, {"commercial", "contracts", "finance"}),
    ("get", "/api/v1/support/tickets/{ticket}/history", {"support", "operations"}, {"commercial", "contracts", "finance"}),
    ("post", "/api/v1/support/tickets/{ticket}/assign", {"support"}, {"commercial", "contracts", "finance", "operations"}),
    ("post", "/api/v1/support/tickets/{ticket}/resolve", {"support"}, {"commercial", "contracts", "finance", "operations"}),
    ("post", "/api/v1/support/tickets/{ticket}/reconcile", {"support", "operations"}, {"commercial", "contracts", "finance"}),
    ("post", "/api/v1/support/tickets/reconcile-pending", {"support", "operations"}, {"commercial", "contracts", "finance"}),
]


@pytest.mark.parametrize(("method", "template", "allowed", "denied"), SUPPORT_ROUTES)
def test_matriz_de_autorizacao_do_atendimento(client, admin_headers, active_contract, monkeypatch, method, template, allowed, denied):
    customer, contract = active_contract
    contracts_available(monkeypatch, False)
    ticket = open_ticket(client, admin_headers, body_for(customer, contract), "t15-roles").json()
    contracts_available(monkeypatch, True)
    path = template.format(ticket=ticket["ticketId"])
    kwargs = {"json": {"owner": "Equipe de assistência"}} if path.endswith("/assign") else {}
    if path == "/api/v1/support/tickets" and method == "post":
        kwargs = {"json": body_for(customer, contract, description="Pane elétrica no pátio")}

    assert_problem(client.request(method, path, **kwargs), 401, "UNAUTHORIZED")
    for role in denied:
        headers = {"Authorization": f"Bearer demo-{role}", "Idempotency-Key": f"roles-{role}"}
        assert_problem(client.request(method, path, headers=headers, **kwargs), 403, "FORBIDDEN")
    for role in allowed:
        headers = {"Authorization": f"Bearer demo-{role}", "Idempotency-Key": f"roles-{role}"}
        response = client.request(method, path, headers=headers, **kwargs)
        # O chamado está pendente: resolver responde 409 pela regra de estado, não pela autorização.
        assert response.status_code not in (401, 403) and response.status_code < 500, f"{role} {method} {path}: {response.text}"


# ---------- Migração aditiva ----------

def test_migracao_0004_preserva_chamados_existentes(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 't15.db'}")
    with engine.begin() as connection:
        command.upgrade(alembic_config(connection), "0003_contract_closing")
        connection.execute(text(
            "INSERT INTO support_tickets (ticket_id, customer_id, contract_id, service_code, category, description, status, priority, sla_hours, due_at) "
            "VALUES ('dddddddd-dddd-4ddd-8ddd-dddddddddddd', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', "
            "'RENTAL-FLEX', 'OUTAGE', 'Chamado legado', 'RESOLVED', 'HIGH', 8, '2026-10-01 18:10:00')"))
    with engine.begin() as connection:
        command.upgrade(alembic_config(connection), "head")
    with Session(engine) as session:
        legacy = session.get(Ticket, "dddddddd-dddd-4ddd-8ddd-dddddddddddd")
        data = TicketService(FakeEntitlementPort(), FakeClock(T0)).as_dict(legacy)
        assert session.query(TicketHistory).count() == 0
    assert (data["status"], data["dueAt"], data["openedAt"], data["resolvedAt"], data["slaStatus"]) == (
        "RESOLVED", "2026-10-01T18:10:00Z", None, None, None)
