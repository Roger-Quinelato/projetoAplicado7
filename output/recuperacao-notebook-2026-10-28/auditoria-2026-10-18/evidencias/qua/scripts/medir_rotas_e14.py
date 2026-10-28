"""F-QUA - E-14: p50/p95 das rotas de negocio de F1 a F3 por HTTP real (uvicorn 127.0.0.1:18103, SQLite da copia).

Uso: python -I medir_rotas_e14.py http://127.0.0.1:18103 <TOKEN_ADMIN_LOCAL_DE_DEMONSTRACAO> <N>

Sequencia por iteracao (igual em espirito a scripts/perf_flows.py de 01/10, mas por HTTP):
  1 POST /api/v1/crm/customers                      (F1, parte A)
  2 POST /api/v1/contracts/drafts                   (F1, parte B)     -> F1 = 1+2
  3 POST /api/v1/contracts/{id}/activate            (F2, parte A)
  4 POST /api/v1/integration/outbox/dispatch        (F2, parte B)     -> F2 = 3+4
  5 POST /api/v1/support/tickets                    (F3, parte A)
  6 POST /api/v1/integration/outbox/dispatch        (F3, parte B)     -> F3 = 5+6
Leituras (N requisicoes cada) e /health/ready como referencia.
Dados sinteticos: e-mails em example.com e Idempotency-Key aleatoria por requisicao.
"""
import statistics
import sys
import time
import uuid

import httpx

BASE, TOKEN, N = sys.argv[1], sys.argv[2], int(sys.argv[3])
client = httpx.Client(base_url=BASE, timeout=60, headers={"Authorization": f"Bearer {TOKEN}"})
samples: dict[str, list[tuple[float, int]]] = {}


def call(name: str, method: str, url: str, **kwargs) -> httpx.Response:
    started = time.perf_counter()
    response = client.request(method, url, **kwargs)
    samples.setdefault(name, []).append(((time.perf_counter() - started) * 1000, response.status_code))
    return response


def idem() -> dict:
    return {"Idempotency-Key": str(uuid.uuid4())}


# Leituras de negocio (N cada) e referencia de saude
for name, url in [
    ("LEITURA F1 GET /api/v1/crm/customers?limit=10", "/api/v1/crm/customers?limit=10&offset=0"),
    ("LEITURA F1 GET /api/v1/contracts/reservations", "/api/v1/contracts/reservations"),
    ("LEITURA F2 GET /api/v1/finance/invoices", "/api/v1/finance/invoices"),
    ("LEITURA F3 GET /api/v1/support/tickets", "/api/v1/support/tickets"),
    ("LEITURA F2/F3 GET /api/v1/workflow/processes", "/api/v1/workflow/processes"),
    ("REFERENCIA GET /health/ready (sem autenticacao)", "/health/ready"),
]:
    for _ in range(N):
        call(name, "GET", url)

# Fluxos F1 a F3 (N iteracoes)
for i in range(N):
    customer = call("F1-A POST /api/v1/crm/customers", "POST", "/api/v1/crm/customers", json={
        "name": f"E14 Sintetico {i}", "email": f"e14-{uuid.uuid4().hex}@example.com",
        "eligible": True, "consentService": True})
    customer.raise_for_status()
    customer_id = customer.json()["customerId"]
    draft = call("F1-B POST /api/v1/contracts/drafts", "POST", "/api/v1/contracts/drafts", headers=idem(), json={
        "customerId": customer_id, "serviceCode": "RENTAL-FLEX", "startsOn": "2027-01-04",
        "billing": {"amount": 1200.0, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8})
    draft.raise_for_status()
    contract_id = draft.json()["contractId"]
    call("F2-A POST /api/v1/contracts/{id}/activate", "POST", f"/api/v1/contracts/{contract_id}/activate", headers=idem())
    call("F2-B POST /api/v1/integration/outbox/dispatch", "POST", "/api/v1/integration/outbox/dispatch")
    ticket = call("F3-A POST /api/v1/support/tickets", "POST", "/api/v1/support/tickets", headers=idem(), json={
        "customerId": customer_id, "contractId": contract_id, "serviceCode": "RENTAL-FLEX",
        "category": "OUTAGE", "description": "Pneu furado sintetico"})
    ticket.raise_for_status()
    call("F3-B POST /api/v1/integration/outbox/dispatch", "POST", "/api/v1/integration/outbox/dispatch")


def p(values: list[float], q: int) -> float:
    return statistics.quantiles(values, n=100, method="inclusive")[q - 1]


def row(name: str, values: list[float], codes: list[int]) -> str:
    bad = sum(1 for c in codes if c >= 400)
    return (f"{name:<62} n={len(values):<4} p50={p(values, 50):8.2f} ms  p95={p(values, 95):8.2f} ms  "
            f"max={max(values):8.2f} ms  nao_2xx={bad}")


print(f"N={N} por rota; base={BASE}; SQLite da copia iso-qua; sem PostgreSQL")
for name, items in samples.items():
    values = [ms for ms, _ in items]
    print(row(name, values, [code for _, code in items]))

print("\nFLUXOS (soma das partes por iteracao)")
for label, parts in [("F1 (cliente + rascunho)", ["F1-A", "F1-B"]), ("F2 (ativar + despachar)", ["F2-A", "F2-B"]),
                     ("F3 (chamado + despachar)", ["F3-A", "F3-B"])]:
    sums = [sum(samples[key][i][0] for key in samples if key.split(" ")[0] in parts) for i in range(N)]
    codes = [code for key in samples if key.split(" ")[0] in parts for _, code in samples[key]]
    print(f"{label:<62} n={len(sums):<4} p50={p(sums, 50):8.2f} ms  p95={p(sums, 95):8.2f} ms  "
          f"max={max(sums):8.2f} ms  nao_2xx={sum(1 for c in codes if c >= 400)}")

worst = max((p([ms for ms, _ in items], 95), name) for name, items in samples.items() if not name.startswith("REFERENCIA"))
print(f"\nMaior p95 entre as rotas de negocio (sem referencia): {worst[0]:.2f} ms em '{worst[1]}'")
print(f"Meta de referencia do projeto (performance_smoke.py): p95 < 500 ms; resultado={'PASS' if worst[0] < 500 else 'FAIL'}")
