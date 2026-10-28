"""Revisão cruzada da F-MOD sobre o DAD-03: broker com porta fechada (sem RabbitMQ), SQLite.

Uso (PYTHONPATH=<iso-mod>\\src, cwd=<iso-mod>):
    python rev_dad_broker.py controle <db_absoluto>   # sem RABBITMQ_URL
    python rev_dad_broker.py quebrado <db_absoluto>   # RABBITMQ_URL apontando para 127.0.0.1:1 (porta fechada)
A porta 1 não tem serviço: a conexão é recusada. Nenhum broker real é iniciado.
"""
import os
import sys
import time
import uuid
from pathlib import Path

MODO, DB = sys.argv[1], Path(sys.argv[2])
if DB.exists():
    os.unlink(DB)
os.environ["DATABASE_URL"] = "sqlite:///" + DB.as_posix()
os.environ.setdefault("FINANCE_ALLOW_FUTURE_AS_OF", "true")
if MODO == "quebrado":
    os.environ["RABBITMQ_URL"] = "amqp://guest:guest@127.0.0.1:1/%2F"
else:
    os.environ.pop("RABBITMQ_URL", None)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from archcorp.finance.models import Invoice  # noqa: E402
from archcorp.infrastructure.db import SessionLocal  # noqa: E402
from archcorp.integration.models import InboxEvent, OutboxEvent  # noqa: E402
from archcorp.main import app  # noqa: E402
from archcorp.workflow.models import ProcessInstance  # noqa: E402

ADMIN, OPS, CON = "demo-admin", "demo-operations", "demo-contracts"


def out(rotulo, valor):
    print(f"RESULTADO | {rotulo} | {valor}", flush=True)


def h(token, key=None):
    headers = {"Authorization": f"Bearer {token}", "X-Correlation-ID": str(uuid.uuid4())}
    if key:
        headers["Idempotency-Key"] = key
    return headers


with TestClient(app) as client:
    out("modo", f"{MODO} (RABBITMQ_URL={'definida' if os.environ.get('RABBITMQ_URL') else 'vazia'})")
    tag = uuid.uuid4().hex[:6]
    cid = client.post("/api/v1/crm/customers", headers=h(ADMIN), json={"name": "Broker Revisao", "email": f"br-{tag}@example.com"}).json()["customerId"]
    contrato = client.post("/api/v1/contracts/drafts", headers=h(CON, key=f"br-d-{tag}"), json={
        "customerId": cid, "serviceCode": "RENTAL-FLEX", "startsOn": "2026-10-20",
        "billing": {"amount": 2500.00, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8}).json()["contractId"]
    r = client.post(f"/api/v1/contracts/{contrato}/activate", headers=h(CON, key=f"br-a-{tag}"))
    out("ativação", r.status_code)
    with SessionLocal() as s:
        evento = s.scalar(select(OutboxEvent).where(OutboxEvent.event_type == "ContractActivated.v1",
                                                    OutboxEvent.payload["contractId"].as_string() == contrato))
        evento_id = evento.event_id
    for n in range(3):
        inicio = time.perf_counter()
        r = client.post("/api/v1/integration/outbox/dispatch", headers=h(OPS))
        duracao = round(time.perf_counter() - inicio, 2)
        with SessionLocal() as s:
            e = s.get(OutboxEvent, evento_id)
            faturas = s.scalars(select(Invoice).where(Invoice.contract_id == contrato)).all()
            processos = s.scalars(select(ProcessInstance).where(ProcessInstance.reference_id == contrato)).all()
            inbox = s.scalars(select(InboxEvent).where(InboxEvent.event_id == evento_id)).all()
            out(f"despacho {n + 1}: duração (s), resposta",
                f"{duracao} s, {r.json()}")
            out(f"despacho {n + 1}: evento (status, attempts, motivo)",
                (e.status, e.attempts, (e.last_error or "")[:70]))
            out(f"despacho {n + 1}: faturas, processos, entradas na inbox", (len(faturas), len(processos), len(inbox)))


if __name__ == "__main__":
    print(f"FIM | modo={MODO} | db={DB.name}", flush=True)
