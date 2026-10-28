"""E-05 (AUD-05 = Q-10): broker RabbitMQ configurado e fora do ar (porta fechada 127.0.0.1:1). SQLite executado.

Fila cheia e recusa (reject-publish/nack) exigem RabbitMQ real: NÃO executado localmente. Cobertura da CI:
tests/test_rabbitmq_real.py (job rabbitmq) e dublês de pika em tests/test_reliability_regressions.py (jobs
rabbitmq e application).
"""
import time

from dad_common import H, activate, customer, draft, rows, scalar, setup

setup("e05.db")
from fastapi.testclient import TestClient  # noqa: E402

from archcorp.config import settings  # noqa: E402
from archcorp.main import app  # noqa: E402


def estado(rotulo):
    eventos = rows("SELECT event_type, status, attempts, substr(coalesce(last_error, ''), 1, 50) "
                   "FROM integration_outbox ORDER BY occurred_at")
    efeitos = {
        "faturas": scalar("SELECT count(*) FROM finance_invoices"),
        "processos": scalar("SELECT count(*) FROM workflow_instances"),
        "inbox": scalar("SELECT count(*) FROM integration_inbox"),
        "auditoria_finance": scalar("SELECT count(*) FROM integration_audit WHERE module = 'finance'"),
    }
    print(f"  {rotulo}: eventos={eventos}")
    print(f"  {rotulo}: efeitos={efeitos}")


with TestClient(app, raise_server_exceptions=False) as c:
    cust = customer(c, "broker")
    activate(c, draft(c, cust, "E05-D0").json()["contractId"], "E05-A0")
    print("controle sem broker:", c.post("/api/v1/integration/outbox/dispatch", headers=H).json())
    estado("após controle")

    settings.rabbitmq_url = "amqp://guest:guest@127.0.0.1:1/%2F"
    activate(c, draft(c, cust, "E05-D1", starts="2027-10-01").json()["contractId"], "E05-A1")
    for i in range(3):
        t0 = time.perf_counter()
        r = c.post("/api/v1/integration/outbox/dispatch", headers=H)
        print(f"despacho {i + 1} com broker fora do ar: http={r.status_code} corpo={r.json()} "
              f"tempo={time.perf_counter() - t0:.2f}s")
        estado(f"após despacho {i + 1}")
    print("falhas:", c.get("/api/v1/integration/failures", headers=H).json())

    settings.rabbitmq_url = None
    activate(c, draft(c, cust, "E05-D2", starts="2027-11-01").json()["contractId"], "E05-A2")
    print("novo evento com broker desligado:", c.post("/api/v1/integration/outbox/dispatch", headers=H).json())
    estado("após broker desligado")
