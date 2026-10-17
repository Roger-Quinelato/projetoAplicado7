"""Demonstração verificável do F2: ativação da locação -> primeira fatura + preparação de retirada, sem duplicidade.

Complementa `scripts/demo_f1.py` (T11) para a T13. Cobre: ativação idempotente com o mesmo eventId, despacho da
outbox, uma fatura INITIAL e um processo ONBOARDING por contrato, despacho repetido sem efeito, ativação repetida
sem novo evento, autorização e trilha por `correlationId`. Usa somente dados sintéticos e a API local; não acessa
sistemas da Localiza.

Uso:
    python scripts/demo_f2.py [--base-url http://localhost:8000] [--token demo-admin] [--forbidden-token demo-support]

Mesmas variáveis e códigos de saída de `demo_f1.py`. Falha permanente e reprocessamento são cobertos por
`tests/test_flows.py::test_falha_permanente_pode_ser_listada_e_reprocessada`, porque a API não expõe um
interruptor para provocar a falha de um consumidor.
"""
import argparse
import os
import sys
from datetime import date, timedelta
from uuid import uuid4

import httpx

from demo_f1 import Demo, is_uuid, safe_json


def invoices_of(demo: Demo, contract_id: str, cid: str) -> list[dict]:
    return safe_json(demo.call("GET", f"/api/v1/finance/invoices?contractId={contract_id}", cid)).get("_list", [])


def onboarding_of(demo: Demo, contract_id: str, cid: str) -> list[dict]:
    processes = safe_json(demo.call("GET", "/api/v1/workflow/processes", cid)).get("_list", [])
    return [p for p in processes if p.get("processType") == "ONBOARDING" and p.get("referenceId") == contract_id]


def run(demo: Demo, forbidden_token: str) -> None:
    run_id = uuid4().hex[:8]
    flow = str(uuid4())
    print(f"== F2 caminho principal (execução {run_id}) | correlationId do fluxo={flow}")

    ready = demo.client.get("/health/ready")
    demo.check("0. API pronta (/health/ready)", ready, [("status UP e banco UP", safe_json(ready) == {"status": "UP", "database": "UP"})])

    customer = safe_json(demo.call("POST", "/api/v1/crm/customers", flow, json={
        "name": f"Cliente Sintético F2 {run_id}", "email": f"f2-{run_id}@cliente-sintetico.example.com"}))
    customer_id = customer.get("customerId")
    starts = (date.today() + timedelta(days=5)).isoformat()
    drafted = demo.call("POST", "/api/v1/contracts/drafts", flow, key=f"demo-f2-draft-{run_id}", json={
        "customerId": customer_id, "serviceCode": "RENTAL-FLEX", "startsOn": starts,
        "billing": {"amount": 1890.00, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8})
    contract_id = safe_json(drafted).get("contractId")
    if not demo.check("1. Cliente e rascunho de contrato preparados (F1)", drafted, [
        ("201", drafted.status_code == 201), ("contractId UUID", is_uuid(contract_id))], f"customerId={customer_id} contractId={contract_id}"):
        return

    activation_key = f"demo-f2-activate-{run_id}"
    path = f"/api/v1/contracts/{contract_id}/activate"
    activated = demo.call("POST", path, flow, key=activation_key)
    body = safe_json(activated)
    event_id = body.get("eventId")
    if not demo.check("2. Ativação grava ACTIVE e ContractActivated.v1 na outbox", activated, [
        ("200", activated.status_code == 200), ("Idempotency-Replayed false", activated.headers.get("Idempotency-Replayed") == "false"),
        ("status ACTIVE", body.get("status") == "ACTIVE"), ("eventId UUID", is_uuid(event_id)),
    ], f"eventId={event_id}"):
        return

    replay = demo.call("POST", path, flow, key=activation_key)
    demo.check("3. Ativação repetida com a mesma chave devolve o mesmo eventId", replay, [
        ("Idempotency-Replayed true", replay.headers.get("Idempotency-Replayed") == "true"),
        ("mesmo eventId", safe_json(replay).get("eventId") == event_id),
    ])

    demo.check("4. Antes do despacho não há fatura nem processo", None, [
        ("sem fatura", invoices_of(demo, contract_id, flow) == []), ("sem preparação de retirada", onboarding_of(demo, contract_id, flow) == []),
    ])

    dispatched = demo.call("POST", "/api/v1/integration/outbox/dispatch", flow)
    demo.check("5. Despacho da outbox entrega o evento a Finance e Workflow", dispatched, [
        ("200", dispatched.status_code == 200), ("pelo menos 1 processado", safe_json(dispatched).get("processed", 0) >= 1),
    ], f"resumo={safe_json(dispatched)}")

    invoices = invoices_of(demo, contract_id, flow)
    demo.check("6. Finance emitiu exatamente uma fatura INITIAL", None, [
        ("1 fatura", len(invoices) == 1),
        ("tipo INITIAL e status OPEN", [(i.get("kind"), i.get("status")) for i in invoices] == [("INITIAL", "OPEN")]),
        ("valor e moeda do contrato", [(i.get("amount"), i.get("currency")) for i in invoices] == [(1890.0, "BRL")]),
        ("origem no eventId da ativação", [i.get("sourceEventId") for i in invoices] == [event_id]),
    ], f"faturas={[(i.get('invoiceId'), i.get('kind'), i.get('amount')) for i in invoices]}")

    processes = onboarding_of(demo, contract_id, flow)
    demo.check("7. Workflow iniciou exatamente uma preparação de retirada", None, [
        ("1 processo ONBOARDING", len(processes) == 1), ("cliente do contrato", [p.get("customerId") for p in processes] == [customer_id]),
    ], f"processos={[(p.get('processId'), p.get('state')) for p in processes]}")

    print("== F2 reentrega e repetição (nenhum efeito pode duplicar)")
    again = demo.call("POST", "/api/v1/integration/outbox/dispatch", flow)
    demo.check("8. Despacho repetido não encontra o evento pendente", again, [("200", again.status_code == 200)], f"resumo={safe_json(again)}")
    demo.call("POST", path, flow, key=activation_key)
    demo.call("POST", "/api/v1/integration/outbox/dispatch", flow)
    demo.check("9. Após ativação e despacho repetidos, continua uma fatura e um processo", None, [
        ("1 fatura", len(invoices_of(demo, contract_id, flow)) == 1), ("1 processo", len(onboarding_of(demo, contract_id, flow)) == 1),
    ])

    other_key = demo.call("POST", path, str(uuid4()), key=f"demo-f2-outra-{run_id}")
    demo.check("10. Nova chave em contrato já ativo devolve a ativação original, sem novo evento", other_key, [
        ("200", other_key.status_code == 200), ("Idempotency-Replayed true", other_key.headers.get("Idempotency-Replayed") == "true"),
        ("mesmo eventId", safe_json(other_key).get("eventId") == event_id),
    ])

    trace = demo.call("GET", f"/api/v1/operations/{flow}", flow)
    audit = [(a.get("module"), a.get("operation")) for a in safe_json(trace).get("audit", [])]
    demo.check("11. Trilha por correlação mostra ativação, cobrança e preparação", trace, [
        ("auditoria contracts", any(m == "contracts" and "activate" in o for m, o in audit)),
        ("auditoria finance", any(m == "finance" for m, _ in audit)),
        ("auditoria workflow", any(m == "workflow" for m, _ in audit)),
    ], "auditoria: " + ", ".join(f"{m}.{o}" for m, o in audit))

    cid = str(uuid4())
    demo.problem("12. Sem credencial -> 401", demo.call("POST", path, cid, key="demo-f2-auth", token=""), 401, "UNAUTHORIZED", cid)
    if forbidden_token:
        cid = str(uuid4())
        demo.problem("13. Papel sem permissão -> 403", demo.call("POST", path, cid, key="demo-f2-auth", token=forbidden_token), 403, "FORBIDDEN", cid)
    else:
        print("[PULO] 13. Papel sem permissão -> 403 (sem --forbidden-token)")

    print(f"== Resumo: cliente={customer_id} contrato={contract_id} eventId={event_id} correlationId={flow}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Demonstração verificável do F2 contra a API local.")
    parser.add_argument("--base-url", default=os.environ.get("ARCHCORP_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--token", default=os.environ.get("ARCHCORP_TOKEN", "demo-admin"))
    parser.add_argument("--forbidden-token", default="demo-support", help="token sem papel de contratos; vazio pula a checagem de 403")
    parser.add_argument("--timeout", type=float, default=10.0, help="timeout por requisição, em segundos")
    args = parser.parse_args()
    try:
        with httpx.Client(base_url=args.base_url, timeout=args.timeout) as client:
            demo = Demo(client, args.token)
            run(demo, args.forbidden_token)
    except httpx.HTTPError as exc:
        print(f"[FALHA] API inacessível em {args.base_url}: {exc.__class__.__name__}")
        return 2
    total = demo.passed + len(demo.failed)
    print(f"== {demo.passed}/{total} checagens aprovadas" + (f"; falharam: {', '.join(demo.failed)}" if demo.failed else ""))
    return 1 if demo.failed or total == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
