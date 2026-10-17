"""Demonstração verificável do F3: chamado com contrato e SLA -> processo de resolução -> resolução.

Complementa `scripts/demo_f1.py` e `scripts/demo_f2.py` (T16). Cobre: elegibilidade e SLA pelo contrato ativo,
abertura idempotente com prioridade e prazo, processo TICKET_RESOLUTION único após o despacho, atribuição,
resolução com `slaStatus`, contrato inexistente -> 422, autorização e trilha por `correlationId`. Usa somente
dados sintéticos e a API local; não acessa sistemas da Localiza.

Uso:
    python scripts/demo_f3.py [--base-url http://localhost:8000] [--token demo-admin] [--forbidden-token demo-finance]

Mesmas variáveis e códigos de saída de `demo_f1.py`. A indisponibilidade de Contracts (PENDING_ENTITLEMENT e
reconciliação) exige reiniciar a API com `CONTRACT_ADAPTER_AVAILABLE=false`; está descrita em
`docs/ROTEIRO_DEMONSTRACAO.md` e coberta por `tests/test_t15_atendimento.py`.
"""
import argparse
import os
import sys
from datetime import date, datetime, timedelta
from uuid import uuid4

import httpx

from demo_f1 import Demo, is_uuid, safe_json


def resolution_of(demo: Demo, ticket_id: str, cid: str) -> list[dict]:
    processes = safe_json(demo.call("GET", "/api/v1/workflow/processes", cid)).get("_list", [])
    return [p for p in processes if p.get("processType") == "TICKET_RESOLUTION" and p.get("referenceId") == ticket_id]


def run(demo: Demo, forbidden_token: str) -> None:
    run_id = uuid4().hex[:8]
    flow = str(uuid4())
    print(f"== F3 caminho principal (execução {run_id}) | correlationId do fluxo={flow}")

    ready = demo.client.get("/health/ready")
    demo.check("0. API pronta (/health/ready)", ready, [("status UP e banco UP", safe_json(ready) == {"status": "UP", "database": "UP"})])

    customer = safe_json(demo.call("POST", "/api/v1/crm/customers", flow, json={
        "name": f"Cliente Sintético F3 {run_id}", "email": f"f3-{run_id}@cliente-sintetico.example.com"}))
    customer_id = customer.get("customerId")
    drafted = safe_json(demo.call("POST", "/api/v1/contracts/drafts", flow, key=f"demo-f3-draft-{run_id}", json={
        "customerId": customer_id, "serviceCode": "RENTAL-FLEX", "startsOn": (date.today() + timedelta(days=2)).isoformat(),
        "billing": {"amount": 990.00, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8}))
    contract_id = drafted.get("contractId")
    activated = demo.call("POST", f"/api/v1/contracts/{contract_id}/activate", flow, key=f"demo-f3-activate-{run_id}")
    if not demo.check("1. Contrato ativo com SLA de 8 h preparado (F1 e F2)", activated, [
        ("200", activated.status_code == 200), ("status ACTIVE", safe_json(activated).get("status") == "ACTIVE")],
            f"customerId={customer_id} contractId={contract_id}"):
        return

    entitlement = demo.call("GET", f"/api/v1/contracts/{contract_id}/entitlement?customerId={customer_id}&serviceCode=RENTAL-FLEX", flow)
    demo.check("2. Contracts confirma elegibilidade e SLA", entitlement, [
        ("200", entitlement.status_code == 200), ("elegível", safe_json(entitlement).get("eligible") is True),
        ("slaHours 8", safe_json(entitlement).get("slaHours") == 8),
    ], f"resposta={safe_json(entitlement)}")

    ticket_key = f"demo-f3-ticket-{run_id}"
    ticket_body = {"customerId": customer_id, "contractId": contract_id, "serviceCode": "RENTAL-FLEX",
                   "category": "OUTAGE", "description": "Veículo sem partida na retirada (sintético)"}
    opened = demo.call("POST", "/api/v1/support/tickets", flow, key=ticket_key, json=ticket_body)
    ticket = safe_json(opened)
    ticket_id = ticket.get("ticketId")
    due_ok = False
    if ticket.get("openedAt") and ticket.get("dueAt"):
        opened_at, due_at = (datetime.fromisoformat(ticket[k].replace("Z", "+00:00")) for k in ("openedAt", "dueAt"))
        due_ok = due_at - opened_at == timedelta(hours=8)
    if not demo.check("3. Support abre o chamado com contrato, SLA e prioridade", opened, [
        ("201", opened.status_code == 201), ("ticketId UUID", is_uuid(ticket_id)), ("status OPEN", ticket.get("status") == "OPEN"),
        ("prioridade HIGH para indisponibilidade", ticket.get("priority") == "HIGH"), ("slaHours 8", ticket.get("slaHours") == 8),
        ("dueAt = openedAt + 8 h", due_ok), ("slaStatus WITHIN", ticket.get("slaStatus") == "WITHIN"),
    ], f"ticketId={ticket_id} dueAt={ticket.get('dueAt')}"):
        return

    replay = demo.call("POST", "/api/v1/support/tickets", flow, key=ticket_key, json=ticket_body)
    demo.check("4. Abertura repetida com a mesma chave devolve o mesmo chamado", replay, [
        ("Idempotency-Replayed true", replay.headers.get("Idempotency-Replayed") == "true"),
        ("mesmo ticketId", safe_json(replay).get("ticketId") == ticket_id),
    ])

    dispatched = demo.call("POST", "/api/v1/integration/outbox/dispatch", flow)
    demo.call("POST", "/api/v1/integration/outbox/dispatch", flow)
    processes = resolution_of(demo, ticket_id, flow)
    demo.check("5. TicketOpened.v1 inicia exatamente um processo de resolução", dispatched, [
        ("despacho 200", dispatched.status_code == 200), ("1 processo TICKET_RESOLUTION", len(processes) == 1),
        ("processo STARTED", [p.get("state") for p in processes] == ["STARTED"]),
    ], f"prazo do chamado={ticket.get('dueAt')} prazo do processo={[p.get('dueAt') for p in processes]} (iguais após o PR #42)")

    assigned = demo.call("POST", f"/api/v1/support/tickets/{ticket_id}/assign", flow, json={"owner": "agente-sintetico-01"})
    demo.check("6. Chamado atribuído a um responsável", assigned, [
        ("200", assigned.status_code == 200), ("responsável registrado", safe_json(assigned).get("owner") == "agente-sintetico-01"),
    ])

    resolve_key = f"demo-f3-resolve-{run_id}"
    resolved = demo.call("POST", f"/api/v1/support/tickets/{ticket_id}/resolve", flow, key=resolve_key)
    demo.check("7. Resolução dentro do prazo fixa slaStatus MET", resolved, [
        ("200", resolved.status_code == 200), ("status RESOLVED", safe_json(resolved).get("status") == "RESOLVED"),
        ("slaStatus MET", safe_json(resolved).get("slaStatus") == "MET"),
    ])
    again = demo.call("POST", f"/api/v1/support/tickets/{ticket_id}/resolve", flow, key=resolve_key)
    demo.check("8. Resolução repetida com a mesma chave não duplica o evento", again, [
        ("Idempotency-Replayed true", again.headers.get("Idempotency-Replayed") == "true"),
    ])

    demo.call("POST", "/api/v1/integration/outbox/dispatch", flow)
    processes = resolution_of(demo, ticket_id, flow)
    demo.check("9. Workflow conclui o processo de resolução", None, [
        ("1 processo", len(processes) == 1), ("estado COMPLETED", [p.get("state") for p in processes] == ["COMPLETED"]),
    ], f"estado={[p.get('state') for p in processes]}")

    history = demo.call("GET", f"/api/v1/support/tickets/{ticket_id}/history", flow)
    events = [h.get("event") or h.get("action") for h in safe_json(history).get("_list", [])]
    demo.check("10. Histórico do chamado registra abertura, atribuição e resolução", history, [
        ("200", history.status_code == 200), ("três marcos", {"OPENED", "ASSIGNED", "RESOLVED"} <= set(events)),
    ], f"histórico={events}")

    trace = demo.call("GET", f"/api/v1/operations/{flow}", flow)
    modules = {a.get("module") for a in safe_json(trace).get("audit", [])}
    demo.check("11. Trilha por correlação reúne Contracts, Support e Workflow", trace, [
        (f"auditoria {m}", m in modules) for m in ("contracts", "support", "workflow")
    ], f"módulos={sorted(m for m in modules if m)}")

    print("== F3 ramificações (cada checagem usa um correlationId próprio)")
    cid = str(uuid4())
    invalid = demo.call("POST", "/api/v1/support/tickets", cid, key=f"demo-f3-invalid-{run_id}", json={**ticket_body, "contractId": str(uuid4())})
    demo.problem("12. Contrato inexistente -> 422", invalid, 422, "BUSINESS_RULE_VIOLATION", cid)

    cid = str(uuid4())
    demo.problem("13. Sem credencial -> 401", demo.call("POST", "/api/v1/support/tickets", cid, key="demo-f3-auth", json=ticket_body, token=""),
                 401, "UNAUTHORIZED", cid)
    if forbidden_token:
        cid = str(uuid4())
        demo.problem("14. Papel sem permissão -> 403", demo.call("POST", "/api/v1/support/tickets", cid, key="demo-f3-auth", json=ticket_body,
                                                                 token=forbidden_token), 403, "FORBIDDEN", cid)
    else:
        print("[PULO] 14. Papel sem permissão -> 403 (sem --forbidden-token)")

    print(f"== Resumo: cliente={customer_id} contrato={contract_id} chamado={ticket_id} correlationId={flow}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Demonstração verificável do F3 contra a API local.")
    parser.add_argument("--base-url", default=os.environ.get("ARCHCORP_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--token", default=os.environ.get("ARCHCORP_TOKEN", "demo-admin"))
    parser.add_argument("--forbidden-token", default="demo-finance", help="token sem papel de atendimento; vazio pula a checagem de 403")
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
