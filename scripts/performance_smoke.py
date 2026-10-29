"""RNF-07: p95 das consultas de negócio da demonstração abaixo de 500 ms (plano de conclusão, pacote F; #62).

Semeia dados sintéticos pelas próprias rotas (clientes, contratos ativos com fatura e preparação,
chamados com processo de resolução) e mede, por consulta, a latência de N chamadas em processo
(TestClient, sem rede). Usa DATABASE_URL quando informado; caso contrário, um SQLite temporário.
O banco indicado é recriado: nunca aponte para um banco com dados que importam.

Uso: PYTHONPATH=src python scripts/performance_smoke.py [--clientes 60] [--amostras 100]
"""
import argparse
import json
import os
import statistics
import time
from datetime import date, timedelta
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./tmp/performance-archcorp.db")
os.environ.pop("RABBITMQ_URL", None)  # mede a API, não a cópia opcional no broker

from fastapi.testclient import TestClient

from archcorp.infrastructure.db import Base, engine
from archcorp.main import app

META_MS = 500
HEADERS = {"Authorization": "Bearer demo-admin"}


def ok(response, status=(200, 201)):
    if response.status_code not in status:
        raise SystemExit(f"Falha ao semear: {response.request.method} {response.request.url} -> {response.status_code} {response.text[:200]}")
    return response.json()


def seed(client: TestClient, customers: int) -> dict:
    """Um contrato ativo e um chamado por cliente; o despacho cria faturas e processos."""
    starts = (date.today() + timedelta(days=1)).isoformat()
    sample = {}
    for index in range(customers):
        customer = ok(client.post("/api/v1/crm/customers", headers=HEADERS, json={
            "name": f"Cliente desempenho {index:03d}", "email": f"perf-{index:03d}@example.com", "eligible": True, "consentService": True}))
        contract = ok(client.post("/api/v1/contracts/drafts", headers={**HEADERS, "Idempotency-Key": f"perf-draft-{index}"}, json={
            "customerId": customer["customerId"], "serviceCode": "RENTAL-FLEX", "startsOn": starts,
            "billing": {"amount": 1000 + index, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8}))
        ok(client.post(f"/api/v1/contracts/{contract['contractId']}/activate", headers={**HEADERS, "Idempotency-Key": f"perf-act-{index}"}))
        ticket = ok(client.post("/api/v1/support/tickets", headers={**HEADERS, "Idempotency-Key": f"perf-ticket-{index}"}, json={
            "customerId": customer["customerId"], "contractId": contract["contractId"], "serviceCode": "RENTAL-FLEX",
            "category": "QUESTION", "description": "Chamado sintético de desempenho"}))
        sample = {"customer": customer["customerId"], "contract": contract["contractId"], "ticket": ticket["ticketId"]}
    dispatched = ok(client.post("/api/v1/integration/outbox/dispatch", headers=HEADERS))
    if dispatched["failed"]:
        raise SystemExit(f"Despacho com falhas ao semear: {dispatched}")
    return sample


def queries(sample: dict) -> dict[str, str]:
    return {
        "CRM: clientes ativos (página)": "/api/v1/crm/customers?active=true&limit=50",
        "CRM: cliente por UUID": f"/api/v1/crm/customers/{sample['customer']}",
        "Contracts: contratos": "/api/v1/contracts",
        "Contracts: elegibilidade e SLA": f"/api/v1/contracts/{sample['contract']}/entitlement?customerId={sample['customer']}&serviceCode=RENTAL-FLEX",
        "Finance: faturas": "/api/v1/finance/invoices",
        "Support: chamados": "/api/v1/support/tickets",
        "Support: histórico do chamado": f"/api/v1/support/tickets/{sample['ticket']}/history",
        "Workflow: processos": "/api/v1/workflow/processes",
        "Workflow: tarefas": "/api/v1/workflow/tasks",
        "Operação: prontidão": "/health/ready",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clientes", type=int, default=60)
    parser.add_argument("--amostras", type=int, default=100)
    parser.add_argument("--json", help="Grava o resultado em JSON neste caminho (consumido por tools/consolidar_evidencias.py).")
    args = parser.parse_args()
    results = []

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    failed = False
    with TestClient(app) as client:
        sample = seed(client, args.clientes)
        print(f"banco={engine.dialect.name} clientes={args.clientes} amostras_por_consulta={args.amostras} meta_p95_ms={META_MS}")
        for label, path in queries(sample).items():
            client.get(path, headers=HEADERS).raise_for_status()  # aquecimento
            samples = []
            for _ in range(args.amostras):
                started = time.perf_counter()
                response = client.get(path, headers=HEADERS)
                samples.append((time.perf_counter() - started) * 1000)
                response.raise_for_status()
            p95 = statistics.quantiles(samples, n=100, method="inclusive")[94]
            failed |= p95 >= META_MS
            results.append({"consulta": label, "p95Ms": round(p95, 2), "medianaMs": round(statistics.median(samples), 2)})
            print(f"{'PASS' if p95 < META_MS else 'FAIL'} p95_ms={p95:7.2f} mediana_ms={statistics.median(samples):7.2f} {label}")
    print(f"resultado={'FAIL' if failed else 'PASS'}")
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps({
            "banco": engine.dialect.name, "clientes": args.clientes, "amostrasPorConsulta": args.amostras, "metaP95Ms": META_MS,
            "maiorP95Ms": max(row["p95Ms"] for row in results), "resultado": "FAIL" if failed else "PASS", "consultas": results,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
