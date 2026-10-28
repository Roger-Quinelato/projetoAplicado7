"""Revisão cruzada da F-MOD sobre a F-DAD: reprodução barata em SQLite (DAD-01, DAD-02, DAD-04, DAD-06, DAD-10).

Código executado: cópia iso-mod (SHA 44b8325), não a pasta da F-DAD. Scripts próprios desta revisão.
Uso (PYTHONPATH=<iso-mod>\\src, cwd=<iso-mod>):
    python rev_dad_sqlite.py intercalacao <db_absoluto>
    python rev_dad_sqlite.py projecao <db_absoluto>
    python rev_dad_sqlite.py valores <db_absoluto>
    python rev_dad_sqlite.py onboarding <db_absoluto>
Sem PostgreSQL, RabbitMQ ou Docker. Dados sintéticos; tokens demo-* do próprio repositório.
Cada resultado sai como "RESULTADO | rótulo | valor observado".
"""
import os
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

CENARIO = sys.argv[1]
DB = Path(sys.argv[2])
if DB.exists():
    os.unlink(DB)
os.environ["DATABASE_URL"] = "sqlite:///" + DB.as_posix()
os.environ.setdefault("FINANCE_ALLOW_FUTURE_AS_OF", "true")
os.environ.pop("RABBITMQ_URL", None)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from archcorp.contracts.models import Contract  # noqa: E402
from archcorp.contracts.service import ContractService  # noqa: E402
from archcorp.crm.service import CustomerService  # noqa: E402
from archcorp.finance.models import Invoice  # noqa: E402
from archcorp.infrastructure.db import SessionLocal  # noqa: E402
from archcorp.integration.models import OutboxEvent  # noqa: E402
from archcorp.main import app, dispatcher  # noqa: E402
from archcorp.workflow.models import ProcessInstance  # noqa: E402

ADMIN, OPS, CON = "demo-admin", "demo-operations", "demo-contracts"


def out(rotulo, valor):
    print(f"RESULTADO | {rotulo} | {valor}", flush=True)


def h(token, key=None, corr=None):
    headers = {"Authorization": f"Bearer {token}", "X-Correlation-ID": corr or str(uuid.uuid4())}
    if key:
        headers["Idempotency-Key"] = key
    return headers


def nome_projecao(contrato):
    from archcorp.contracts.models import Contract as C
    with SessionLocal() as s:
        return s.get(C, contrato).customer_name


def status_evento(event_id):
    with SessionLocal() as s:
        e = s.get(OutboxEvent, event_id)
        return {"status": e.status, "attempts": e.attempts, "last_error": (e.last_error or "")[:60]}


def cenario_intercalacao(client):
    clientes = CustomerService()
    contratos = ContractService(clientes)
    with SessionLocal() as s:
        cid = clientes.create(s, {"name": "Cliente Revisao", "email": f"rev-{uuid.uuid4().hex[:6]}@example.com"},
                              str(uuid.uuid4())).customer_id
    with SessionLocal() as s:
        draft = {"customerId": cid, "serviceCode": "RENTAL-FLEX", "startsOn": date(2026, 10, 20),
                 "billing": {"amount": 2500.00, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8}
        contrato = contratos.create_draft(s, draft, f"rev-draft-{uuid.uuid4().hex[:6]}", str(uuid.uuid4()))[0]["contractId"]
    # Sessão A lê DRAFT e libera a transação; a sessão B ativa por completo; A age com a leitura antiga.
    sessao_a, sessao_b = SessionLocal(), SessionLocal()
    sessao_a.get(Contract, contrato)
    sessao_a.commit()
    resp_b, _ = contratos.activate(sessao_b, contrato, "rev-act-B", str(uuid.uuid4()))
    resp_a, replay_a = contratos.activate(sessao_a, contrato, "rev-act-A", str(uuid.uuid4()))
    with SessionLocal() as s:
        eventos = [e for e in s.scalars(select(OutboxEvent).where(OutboxEvent.event_type == "ContractActivated.v1")).all()
                   if e.payload.get("contractId") == contrato]
        out("intercalação: eventos ContractActivated.v1 para o mesmo contrato", len(eventos))
        out("intercalação: eventIds distintos", sorted({e.event_id[:8] for e in eventos}))
        out("intercalação: replay retornado à sessão A", replay_a)
    sessao_a.close()
    sessao_b.close()
    with SessionLocal() as s:
        out("intercalação: status final do contrato", s.get(Contract, contrato).status)


def cenario_projecao(client):
    tag = uuid.uuid4().hex[:6]
    cid = client.post("/api/v1/crm/customers", headers=h(ADMIN), json={"name": "Nome Versao 0", "email": f"proj-{tag}@example.com"}).json()["customerId"]
    contrato = client.post("/api/v1/contracts/drafts", headers=h(CON, key=f"proj-d-{tag}"), json={
        "customerId": cid, "serviceCode": "RENTAL-FLEX", "startsOn": "2026-10-20",
        "billing": {"amount": 2500.00, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8}).json()["contractId"]
    client.patch(f"/api/v1/crm/customers/{cid}", headers=h(ADMIN), json={"name": "Nome Versao 1"})
    client.patch(f"/api/v1/crm/customers/{cid}", headers=h(ADMIN), json={"name": "Nome Versao 2"})
    with SessionLocal() as s:
        eventos = [e for e in s.scalars(select(OutboxEvent).where(OutboxEvent.event_type == "CustomerUpdated.v1")
                                        .order_by(OutboxEvent.occurred_at)).all() if e.payload.get("customerId") == cid]
        e1, e2 = eventos[0].event_id, eventos[1].event_id
        out("projeção: eventos CustomerUpdated.v1 gerados", [e.payload["name"] for e in eventos])
    handlers = dispatcher.handlers["CustomerUpdated.v1"]
    original = handlers[0]

    def falha_na_v1(session, envelope):
        if envelope["payload"]["name"] == "Nome Versao 1":
            raise RuntimeError("falha injetada (revisão)")
        return original[1](session, envelope)

    handlers[0] = (original[0], falha_na_v1)
    instantes = []
    for n in range(3):
        inicio = time.perf_counter()
        r = client.post("/api/v1/integration/outbox/dispatch", headers=h(OPS))
        instantes.append(round(time.perf_counter() - inicio, 3))
        out(f"projeção: despacho {n + 1} (com v1 falhando)", r.json())
    out("projeção: intervalos entre despachos (s), sem backoff se forem curtos", instantes)
    out("projeção: evento v1 após 3 despachos", status_evento(e1))
    out("projeção: evento v2 após 3 despachos", status_evento(e2))
    out("projeção: nome na projeção após v2 aplicada", nome_projecao(contrato))
    handlers[0] = original
    r = client.post(f"/api/v1/integration/failures/{e1}/reprocess", headers=h(OPS, corr=(corr := str(uuid.uuid4()))))
    out("projeção: reprocessamento da v1", r.status_code)
    client.post("/api/v1/integration/outbox/dispatch", headers=h(OPS))
    out("projeção: nome na projeção após reprocessar v1 (esperado: Nome Versao 2)", nome_projecao(contrato))
    trilha = client.get(f"/api/v1/operations/{corr}", headers=h(OPS)).json()
    out("projeção: auditoria do reprocessamento (details)", [a["details"] for a in trilha["audit"] if a["operation"] == "reprocess_event"])
    # DAD-04 (lote sem limite): 250 eventos pendentes saem num único despacho?
    with SessionLocal() as s:
        for _ in range(250):
            s.add(OutboxEvent(event_type="TicketResolved.v1", producer="support", correlation_id=str(uuid.uuid4()),
                              payload={"ticketId": str(uuid.uuid4())}, status="PENDING", attempts=0))
        s.commit()
    r = client.post("/api/v1/integration/outbox/dispatch", headers=h(OPS))
    out("lote: 250 pendentes em um despacho (processed, failed)", r.json())


def cenario_valores(client):
    tag = uuid.uuid4().hex[:6]
    cid = client.post("/api/v1/crm/customers", headers=h(ADMIN), json={"name": "Valores Revisao", "email": f"val-{tag}@example.com"}).json()["customerId"]
    for rotulo, valor in (("1e12", "1e12"), ("1e15", "1e15"), ("999999999999.99", "999999999999.99")):
        corpo = ('{"customerId":"%s","serviceCode":"RENTAL-FLEX","startsOn":"2026-10-20","billing":{"amount":%s,'
                 '"currency":"BRL","cycle":"MONTHLY"},"slaHours":8}' % (cid, valor))
        r = client.post("/api/v1/contracts/drafts", content=corpo.encode(), headers={
            **h(CON, key=f"val-{rotulo}-{tag}"), "Content-Type": "application/json"})
        out(f"rascunho com amount={rotulo}", r.status_code)
        if r.status_code == 201:
            out(f"rascunho {rotulo}: tipo de billing.amount na resposta", type(r.json()["billing"]["amount"]).__name__ + " " + str(r.json()["billing"]["amount"]))
            contrato = r.json()["contractId"]
            lido = client.get(f"/api/v1/contracts/{contrato}", headers=h(CON)).json()
            out(f"rascunho {rotulo}: tipo de billing.amount no GET", type(lido["billing"]["amount"]).__name__ + " " + str(lido["billing"]["amount"]))
    for rotulo, valor in (("1e12", "1e12"), ("1e15", "1e15")):
        corpo = ('{"customerId":"%s","vehicleGroup":"SUV","protectionCode":"BASICA","serviceCode":"RENTAL-FLEX",'
                 '"startsOn":"2026-11-02","endsOn":"2026-11-05","amount":%s,"currency":"BRL","billingCycle":"ONCE","slaHours":8}'
                 % (cid, valor))
        r = client.post("/api/v1/contracts/reservations", content=corpo.encode(), headers={
            **h(CON), "Content-Type": "application/json"})
        out(f"reserva com amount={rotulo}", r.status_code)
    from archcorp.finance.routes import PaymentInput
    from pydantic import ValidationError
    for valor in ("1e12", "1e15", "999999999999.99"):
        try:
            PaymentInput(amount=Decimal(valor), currency="BRL", reference="REV-PAG-001")
            out(f"pagamento (schema) amount={valor}", "aceito")
        except ValidationError as exc:
            out(f"pagamento (schema) amount={valor}", "recusado: " + exc.errors()[0]["type"])


def cenario_onboarding(client):
    from archcorp.workflow.service import handle_contract_activated
    ocorrido = datetime.now(timezone.utc) - timedelta(hours=10)
    contrato = str(uuid.uuid4())
    envelope = {"eventId": str(uuid.uuid4()), "eventType": "ContractActivated.v1", "eventVersion": 1,
                "occurredAt": ocorrido.isoformat().replace("+00:00", "Z"), "correlationId": str(uuid.uuid4()),
                "causationId": None, "producer": "contracts",
                "payload": {"contractId": contrato, "customerId": str(uuid.uuid4())}}
    processamento = datetime.now(timezone.utc)
    with SessionLocal() as s:
        handle_contract_activated(s, envelope)
        s.commit()
    with SessionLocal() as s:
        due = s.scalar(select(ProcessInstance.due_at).where(ProcessInstance.reference_id == contrato))
    due = due.replace(tzinfo=timezone.utc) if due.tzinfo is None else due
    out("onboarding: horas entre occurredAt e dueAt (esperado 72 se contado do evento; 82 se do despacho)",
        round((due - ocorrido).total_seconds() / 3600, 2))
    out("onboarding: horas entre o processamento e dueAt", round((due - processamento).total_seconds() / 3600, 2))


if __name__ == "__main__":
    with TestClient(app) as client:
        {"intercalacao": lambda c: cenario_intercalacao(c), "projecao": cenario_projecao,
         "valores": cenario_valores, "onboarding": cenario_onboarding}[CENARIO](client)
    print(f"FIM | cenario={CENARIO} | db={DB.name}", flush=True)
