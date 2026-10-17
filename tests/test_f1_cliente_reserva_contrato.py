"""T11 · F1 ponta a ponta: cliente do CRM -> reserva -> rascunho de contrato sem recadastro.

Complementa `test_f1_cria_rascunho_sem_recadastro_e_reutiliza_idempotencia` (rascunho direto)
com o caminho pela reserva e com as ramificações do plano (PLANO_IMPLEMENTACAO_CENARIO_4.md, F1):
validação 4xx, cliente rejeitado, indisponibilidade do adaptador, idempotência e erro rastreado.
"""
import io
import json
import logging
from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from archcorp import main
from archcorp.contracts.adapters import ResilientCustomerReader
from archcorp.contracts.models import Contract, Reservation
from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import AuditLog, IdempotencyRecord
from archcorp.observability import JsonFormatter

MISSING_ID = "99999999-9999-4999-8999-999999999999"
PROBLEM_FIELDS = {"type", "title", "status", "detail", "instance", "code", "correlationId"}
CADASTRAL_FIELDS = {"name", "email", "customerName", "customerEmail", "eligible", "consentService", "active", "legacyId", "phone"}


def future(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def reservation_body(customer_id: str, **overrides) -> dict:
    return {"customerId": customer_id, "vehicleGroup": "SUV-COMPACTO", "protectionCode": "BASICA", "serviceCode": "RENTAL-FLEX",
            "startsOn": future(3), "endsOn": future(6), "amount": 750, "currency": "BRL", "billingCycle": "ONCE", "slaHours": 8, **overrides}


def draft_body(customer_id: str, **overrides) -> dict:
    return {"customerId": customer_id, "serviceCode": "RENTAL-FLEX", "startsOn": "2027-01-04",
            "billing": {"amount": 2500, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8, **overrides}


def assert_problem(response, status: int, code: str, correlation_id: str | None = None) -> dict:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert PROBLEM_FIELDS.issubset(body)
    assert (body["status"], body["code"]) == (status, code)
    assert body["correlationId"] == response.headers["X-Correlation-ID"]
    if correlation_id:
        assert body["correlationId"] == correlation_id
    return body


def contracts_in_db() -> list[Contract]:
    with SessionLocal() as session:
        return list(session.scalars(select(Contract)))


@pytest.fixture
def crm_customer(client, admin_headers):
    response = client.post("/api/v1/crm/customers", headers=admin_headers, json={
        "name": "Locadora Cliente F1 Ltda.", "email": "f1@cliente-sintetico.example.com", "legacyId": "SINT-F1-1",
    })
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def reservation(client, admin_headers, crm_customer):
    response = client.post("/api/v1/contracts/reservations", headers={**admin_headers, "Idempotency-Key": "f1-reservation"},
                           json=reservation_body(crm_customer["customerId"]))
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def json_logs():
    """Captura as linhas JSON do logger da aplicação no momento da emissão (com o correlationId do contexto)."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("archcorp")
    logger.addHandler(handler)
    try:
        yield lambda: [json.loads(line) for line in stream.getvalue().splitlines() if line.startswith("{")]
    finally:
        logger.removeHandler(handler)


def test_f1_reserva_origina_rascunho_com_cliente_do_crm_sem_recadastro(client, admin_headers, crm_customer, reservation):
    customer_id = crm_customer["customerId"]
    assert reservation["customerId"] == customer_id
    assert (reservation["status"], reservation["contractId"]) == ("REQUESTED", None)

    path = f"/api/v1/contracts/reservations/{reservation['reservationId']}/draft"
    drafted = client.post(path, headers={**admin_headers, "Idempotency-Key": "f1-draft"})
    assert drafted.status_code == 200, drafted.text
    assert drafted.headers["Idempotency-Replayed"] == "false"
    contract = drafted.json()["contract"]
    assert contract["customerId"] == customer_id
    assert contract["status"] == "DRAFT"
    assert {k: contract[k] for k in ("serviceCode", "startsOn", "endsOn", "slaHours")} == {k: reservation[k] for k in ("serviceCode", "startsOn", "endsOn", "slaHours")}
    assert contract["billing"] == {"amount": reservation["amount"], "currency": reservation["currency"], "cycle": reservation["billingCycle"]}
    assert client.get(f"/api/v1/contracts/{contract['contractId']}", headers=admin_headers).json() == contract

    linked = client.get(f"/api/v1/contracts/reservations/{reservation['reservationId']}", headers=admin_headers).json()
    assert (linked["status"], linked["contractId"]) == ("DRAFTED", contract["contractId"])

    for key in ("f1-draft", "f1-draft-outra-tentativa"):
        repeated = client.post(path, headers={**admin_headers, "Idempotency-Key": key})
        assert repeated.status_code == 200, repeated.text
        assert repeated.headers["Idempotency-Replayed"] == "true"
        assert repeated.json()["contract"]["contractId"] == contract["contractId"]

    # A projeção do contrato vem do CRM (CustomerReader), não do pedido: nenhum dado cadastral foi reenviado.
    stored = contracts_in_db()
    assert len(stored) == 1
    assert (stored[0].customer_id, stored[0].customer_name, stored[0].customer_email) == (customer_id, crm_customer["name"], crm_customer["email"])
    legacy = client.get("/api/v1/integration/legacy-ids/CRM/SINT-F1-1", headers=admin_headers).json()
    assert legacy["globalId"] == contract["customerId"]


def test_f1_contratos_de_entrada_nao_aceitam_dados_cadastrais():
    schema = main.app.openapi()
    components = schema["components"]["schemas"]
    for name in ("ContractDraftCreate", "ReservationInput"):
        properties = set(components[name]["properties"])
        assert "customerId" in properties
        assert properties.isdisjoint(CADASTRAL_FIELDS), name
    assert "requestBody" not in schema["paths"]["/api/v1/contracts/reservations/{reservation_id}/draft"]["post"]


def test_f1_cliente_rejeitado_nao_deixa_efeito_parcial_nem_consome_a_chave(client, admin_headers, crm_customer, reservation, json_logs):
    missing_cid = str(uuid4())
    missing = client.post("/api/v1/contracts/drafts", headers={**admin_headers, "X-Correlation-ID": missing_cid, "Idempotency-Key": "f1-missing"},
                          json=draft_body(MISSING_ID))
    assert assert_problem(missing, 422, "BUSINESS_RULE_VIOLATION", missing_cid)["detail"] == "Cliente inexistente ou inelegível"
    # Erro rastreado: a linha de log da requisição carrega o mesmo correlationId e o status.
    assert any(line["correlationId"] == missing_cid and line["result"] == 422 for line in json_logs())

    path = f"/api/v1/contracts/reservations/{reservation['reservationId']}/draft"
    customer_path = f"/api/v1/crm/customers/{crm_customer['customerId']}"
    assert client.patch(customer_path, headers=admin_headers, json={"consentService": False}).status_code == 200
    rejected = client.post(path, headers={**admin_headers, "Idempotency-Key": "f1-consent"})
    assert_problem(rejected, 422, "BUSINESS_RULE_VIOLATION")
    still = client.get(f"/api/v1/contracts/reservations/{reservation['reservationId']}", headers=admin_headers).json()
    assert (still["status"], still["contractId"]) == ("REQUESTED", None)
    assert contracts_in_db() == []
    with SessionLocal() as session:
        assert session.scalar(select(IdempotencyRecord).where(IdempotencyRecord.key.in_(["f1-missing", "f1-consent"]))) is None

    # A rejeição não consome a chave: corrigido o consentimento no CRM, a mesma chave cria o rascunho uma vez.
    assert client.patch(customer_path, headers=admin_headers, json={"consentService": True}).status_code == 200
    accepted = client.post(path, headers={**admin_headers, "Idempotency-Key": "f1-consent"})
    assert accepted.status_code == 200, accepted.text
    assert accepted.headers["Idempotency-Replayed"] == "false"
    assert [c.customer_id for c in contracts_in_db()] == [crm_customer["customerId"]]


@pytest.mark.parametrize(("change", "removed", "loc"), [
    ({"billing": {"amount": 0, "currency": "BRL", "cycle": "MONTHLY"}}, None, ["body", "billing", "amount"]),
    ({"billing": {"amount": 10.555, "currency": "BRL", "cycle": "MONTHLY"}}, None, ["body", "billing", "amount"]),
    ({"billing": {"amount": 100, "currency": "brl", "cycle": "MONTHLY"}}, None, ["body", "billing", "currency"]),
    ({"billing": {"amount": 100, "currency": "BRL", "cycle": "WEEKLY"}}, None, ["body", "billing", "cycle"]),
    ({}, "billing", ["body", "billing"]),
    ({"serviceCode": "X"}, None, ["body", "serviceCode"]),
    ({"startsOn": "2027-02-30"}, None, ["body", "startsOn"]),
    ({"slaHours": 0}, None, ["body", "slaHours"]),
])
def test_f1_validacao_estrutural_do_rascunho_retorna_422_sem_criar_contrato(client, admin_headers, crm_customer, change, removed, loc):
    body = draft_body(crm_customer["customerId"], **change)
    if removed:
        body.pop(removed)
    response = client.post("/api/v1/contracts/drafts", headers={**admin_headers, "Idempotency-Key": "f1-invalid"}, json=body)
    problem = assert_problem(response, 422, "VALIDATION_ERROR", admin_headers["X-Correlation-ID"])
    assert loc in [error["loc"] for error in problem["errors"]]
    assert contracts_in_db() == []


def test_f1_rascunho_da_reserva_valida_cabecalho_recurso_e_papel(client, admin_headers, reservation):
    path = f"/api/v1/contracts/reservations/{reservation['reservationId']}/draft"
    no_key = assert_problem(client.post(path, headers=admin_headers), 422, "VALIDATION_ERROR")
    assert ["header", "Idempotency-Key"] in [error["loc"] for error in no_key["errors"]]
    assert_problem(client.post("/api/v1/contracts/reservations/nao-uuid/draft", headers={**admin_headers, "Idempotency-Key": "k"}), 422, "VALIDATION_ERROR")
    missing = client.post(f"/api/v1/contracts/reservations/{MISSING_ID}/draft", headers={**admin_headers, "Idempotency-Key": "k"})
    assert assert_problem(missing, 404, "NOT_FOUND")["detail"] == "Reserva não encontrada"

    for url, body in ((path, None), ("/api/v1/contracts/drafts", draft_body(reservation["customerId"]))):
        assert_problem(client.post(url, headers={"Idempotency-Key": "auth"}, json=body), 401, "UNAUTHORIZED")
        for role in ("finance", "support", "operations"):
            denied = client.post(url, headers={"Authorization": f"Bearer demo-{role}", "Idempotency-Key": "auth"}, json=body)
            assert_problem(denied, 403, "FORBIDDEN")
    assert contracts_in_db() == []
    assert client.get(f"/api/v1/contracts/reservations/{reservation['reservationId']}", headers=admin_headers).json()["status"] == "REQUESTED"


class UnavailableCustomerReader:
    """Simula o CRM sem resposta (timeout), sem tocar no módulo CRM."""

    def __init__(self):
        self.calls = 0

    def get(self, session, customer_id):
        self.calls += 1
        raise TimeoutError("CRM sem resposta no prazo (simulado)")


class FlakyCustomerReader:
    """Falha de forma transitória nas primeiras chamadas e depois delega ao CRM real."""

    def __init__(self, failures: int, error: Exception):
        self.failures, self.error, self.calls = failures, error, 0

    def get(self, session, customer_id):
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error
        return main.customers.get(session, customer_id)


def resilient(inner, attempts=3):
    """Envolve o leitor simulado com o adaptador de produção, sem esperar de fato entre tentativas."""
    return ResilientCustomerReader(inner, timeout_seconds=5, max_attempts=attempts, base_delay_seconds=0.1, sleep=lambda _: None)


def test_f1_indisponibilidade_do_crm_retorna_503_sem_efeito_parcial(client, admin_headers, reservation, monkeypatch, json_logs):
    path = f"/api/v1/contracts/reservations/{reservation['reservationId']}/draft"
    correlation_id = str(uuid4())
    headers = {**admin_headers, "X-Correlation-ID": correlation_id, "Idempotency-Key": "f1-timeout"}
    unavailable = UnavailableCustomerReader()
    with monkeypatch.context() as patch:
        patch.setattr(main.contracts, "customers", resilient(unavailable))
        failed = client.post(path, headers=headers)
    # ADR-006: retentativa limitada ao erro transitório; ao esgotar, 503 sem gravar contrato, chave ou auditoria.
    problem = assert_problem(failed, 503, "SERVICE_UNAVAILABLE", correlation_id)
    assert "CRM sem resposta" not in json.dumps(problem)
    assert unavailable.calls == 3
    retries = [line for line in json_logs() if line["correlationId"] == correlation_id and line["level"] == "WARNING"]
    assert len(retries) == 3
    assert client.get(f"/api/v1/contracts/reservations/{reservation['reservationId']}", headers=admin_headers).json()["status"] == "REQUESTED"
    assert contracts_in_db() == []
    with SessionLocal() as session:
        assert session.scalar(select(IdempotencyRecord).where(IdempotencyRecord.key == "f1-timeout")) is None
        assert session.scalar(select(AuditLog).where(AuditLog.correlation_id == correlation_id)) is None

    # O chamador repete com a mesma chave após o retorno do CRM e recebe um único contrato.
    retried = client.post(path, headers=headers)
    assert retried.status_code == 200, retried.text
    assert retried.headers["Idempotency-Replayed"] == "false"
    again = client.post(path, headers=headers)
    assert again.headers["Idempotency-Replayed"] == "true"
    assert again.json()["contract"]["contractId"] == retried.json()["contract"]["contractId"]
    assert len(contracts_in_db()) == 1


def test_f1_falha_transitoria_do_crm_e_absorvida_pela_retentativa(client, admin_headers, reservation, monkeypatch):
    flaky = FlakyCustomerReader(failures=2, error=ConnectionError("CRM recusou a conexão (simulado)"))
    with monkeypatch.context() as patch:
        patch.setattr(main.contracts, "customers", resilient(flaky))
        drafted = client.post(f"/api/v1/contracts/reservations/{reservation['reservationId']}/draft",
                              headers={**admin_headers, "Idempotency-Key": "f1-flaky"})
    assert drafted.status_code == 200, drafted.text
    assert flaky.calls == 3
    assert len(contracts_in_db()) == 1


def test_f1_erro_nao_transitorio_do_crm_nao_e_repetido(client, admin_headers, reservation, monkeypatch):
    broken = FlakyCustomerReader(failures=5, error=ValueError("resposta inválida do CRM (simulado)"))
    with monkeypatch.context() as patch:
        patch.setattr(main.contracts, "customers", resilient(broken))
        failed = client.post(f"/api/v1/contracts/reservations/{reservation['reservationId']}/draft",
                             headers={**admin_headers, "Idempotency-Key": "f1-broken"})
    assert_problem(failed, 500, "INTERNAL_ERROR")
    assert broken.calls == 1
    assert contracts_in_db() == []


def test_f1_reserva_e_ativacao_tambem_respondem_503_com_crm_indisponivel(client, admin_headers, crm_customer, monkeypatch):
    customer = crm_customer
    draft = client.post("/api/v1/contracts/drafts", headers={**admin_headers, "Idempotency-Key": "f1-503-draft"}, json=draft_body(customer["customerId"]))
    assert draft.status_code == 201, draft.text
    with monkeypatch.context() as patch:
        patch.setattr(main.contracts, "customers", resilient(UnavailableCustomerReader()))
        reservation = client.post("/api/v1/contracts/reservations", headers={**admin_headers, "Idempotency-Key": "f1-503-res"},
                                  json=reservation_body(customer["customerId"]))
        activation = client.post(f"/api/v1/contracts/{draft.json()['contractId']}/activate",
                                 headers={**admin_headers, "Idempotency-Key": "f1-503-act"})
    assert_problem(reservation, 503, "SERVICE_UNAVAILABLE")
    assert_problem(activation, 503, "SERVICE_UNAVAILABLE")
    assert client.get(f"/api/v1/contracts/{draft.json()['contractId']}", headers=admin_headers).json()["status"] == "DRAFT"


def test_f1_correlation_id_atravessa_http_auditoria_e_trilha(client, admin_headers):
    correlation_id = str(uuid4())
    headers = {**admin_headers, "X-Correlation-ID": correlation_id}
    customer = client.post("/api/v1/crm/customers", headers=headers, json={"name": "Cliente Trilha F1", "email": "trilha-f1@example.com"})
    created = client.post("/api/v1/contracts/reservations", headers={**headers, "Idempotency-Key": "f1-trace-res"}, json=reservation_body(customer.json()["customerId"]))
    drafted = client.post(f"/api/v1/contracts/reservations/{created.json()['reservationId']}/draft", headers={**headers, "Idempotency-Key": "f1-trace-draft"})
    for response in (customer, created, drafted):
        assert response.status_code in (200, 201), response.text
        assert response.headers["X-Correlation-ID"] == correlation_id
    customer_id, reservation_id = customer.json()["customerId"], created.json()["reservationId"]
    contract_id = drafted.json()["contract"]["contractId"]

    trace = client.get(f"/api/v1/operations/{correlation_id}", headers=admin_headers)
    assert trace.status_code == 200, trace.text
    steps = [(a["module"], a["operation"], a["entityId"]) for a in trace.json()["audit"]]
    assert ("crm", "create_customer", customer_id) in steps
    assert ("contracts", "create_reservation", reservation_id) in steps
    assert ("contracts", "create_draft", contract_id) in steps
    assert ("contracts", "draft_from_reservation", reservation_id) in steps
    assert steps.index(("crm", "create_customer", customer_id)) < steps.index(("contracts", "create_reservation", reservation_id))
    link = next(a for a in trace.json()["audit"] if a["operation"] == "draft_from_reservation")
    assert link["details"] == {"contractId": contract_id}

    # Sem cabeçalho, a API gera o UUID, devolve-o e o usa na auditoria.
    generated = client.post("/api/v1/contracts/drafts", headers={"Authorization": admin_headers["Authorization"], "Idempotency-Key": "f1-generated"},
                            json=draft_body(customer_id))
    assert generated.status_code == 201, generated.text
    generated_id = str(UUID(generated.headers["X-Correlation-ID"]))
    audit = client.get(f"/api/v1/operations/{generated_id}", headers=admin_headers).json()["audit"]
    assert [(a["operation"], a["entityId"]) for a in audit] == [("create_draft", generated.json()["contractId"])]


def test_f1_mesma_chave_em_outra_reserva_nao_vincula_contrato_alheio(client, admin_headers, crm_customer):
    body = reservation_body(crm_customer["customerId"])
    first = client.post("/api/v1/contracts/reservations", headers=admin_headers, json=body).json()
    second = client.post("/api/v1/contracts/reservations", headers=admin_headers, json={**body, "vehicleGroup": "SEDAN-EXECUTIVO"}).json()
    key = {**admin_headers, "Idempotency-Key": "f1-shared-key"}
    drafted = client.post(f"/api/v1/contracts/reservations/{first['reservationId']}/draft", headers=key)
    assert drafted.status_code == 200, drafted.text
    contract_id = drafted.json()["contract"]["contractId"]

    reused = client.post(f"/api/v1/contracts/reservations/{second['reservationId']}/draft", headers=key)
    assert_problem(reused, 409, "IDEMPOTENCY_CONFLICT")
    untouched = client.get(f"/api/v1/contracts/reservations/{second['reservationId']}", headers=admin_headers).json()
    assert (untouched["status"], untouched["contractId"]) == ("REQUESTED", None)

    # Cancelar a outra reserva não pode cancelar o contrato da primeira.
    assert client.post(f"/api/v1/contracts/reservations/{second['reservationId']}/cancel", headers=admin_headers).json()["status"] == "CANCELLED"
    assert client.get(f"/api/v1/contracts/{contract_id}", headers=admin_headers).json()["status"] == "DRAFT"
    with SessionLocal() as session:
        assert session.scalars(select(Reservation.reservation_id).where(Reservation.contract_id == contract_id)).all() == [first["reservationId"]]


@pytest.mark.parametrize("same_terms", [True, False], ids=["mesmas-condicoes", "outras-condicoes"])
def test_f1_chave_do_rascunho_direto_reaproveitada_na_reserva_retorna_409(client, admin_headers, crm_customer, reservation, same_terms):
    starts_on = reservation["startsOn"] if same_terms else "2027-03-01"
    direct = client.post("/api/v1/contracts/drafts", headers={**admin_headers, "Idempotency-Key": "f1-cross-route"}, json=draft_body(
        crm_customer["customerId"], startsOn=starts_on, slaHours=reservation["slaHours"],
        billing={"amount": reservation["amount"], "currency": reservation["currency"], "cycle": reservation["billingCycle"]}))
    assert direct.status_code == 201, direct.text

    reused = client.post(f"/api/v1/contracts/reservations/{reservation['reservationId']}/draft", headers={**admin_headers, "Idempotency-Key": "f1-cross-route"})
    assert_problem(reused, 409, "IDEMPOTENCY_CONFLICT")
    untouched = client.get(f"/api/v1/contracts/reservations/{reservation['reservationId']}", headers=admin_headers).json()
    assert (untouched["status"], untouched["contractId"]) == ("REQUESTED", None)
    assert [c.contract_id for c in contracts_in_db()] == [direct.json()["contractId"]]
    with SessionLocal() as session:
        assert session.scalar(select(AuditLog).where(AuditLog.operation == "draft_from_reservation")) is None
