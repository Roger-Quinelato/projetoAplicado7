"""Revisão cruzada de QUA-02 (independente): famílias e campos de /metrics após requisições reais (SQLite)."""
from dad_common import H, customer, setup

setup("rev_qua02.db")
from fastapi.testclient import TestClient  # noqa: E402

from archcorp.main import app  # noqa: E402


def familias(texto):
    nomes = set()
    for linha in texto.splitlines():
        if linha and not linha.startswith("#"):
            nomes.add(linha.split("{")[0].split(" ")[0])
    return sorted(nomes)


with TestClient(app) as c:
    for _ in range(60):
        c.get("/health/live")
    c.get("/api/v1/demo/state", headers=H)
    print("1) após 61 requisições:", familias(c.get("/metrics", headers=H).text))
    cust = customer(c, "metric")
    c.patch(f"/api/v1/crm/customers/{cust['customerId']}", headers=H, json={"name": "Nome Métrico"})
    print("   dispatch:", c.post("/api/v1/integration/outbox/dispatch", headers=H).json())
    texto = c.get("/metrics", headers=H).text
    print("2) após publicar um evento:", familias(texto))
    print("   linhas de latência (amostra):", [linha for linha in texto.splitlines() if "latency" in linha][:2])
    print("   contém _count, _bucket ou retry:", any(x in texto for x in ("_count", "_bucket", "retr")))
    print("   broker_queue_messages presente (sem broker configurado):", "broker_queue_messages" in texto)
