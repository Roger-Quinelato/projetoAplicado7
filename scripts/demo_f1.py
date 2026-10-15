"""Demonstração verificável do F1: cliente do CRM -> reserva -> rascunho de contrato sem recadastro.

Equivalente portátil (Windows, Linux, macOS) da parte F1 de `scripts/demo.ps1`, com as ramificações
do plano: validação 4xx, cliente inexistente/inativo, idempotência, autorização e erro rastreado por
`correlationId`. Usa somente dados sintéticos e a API local; não acessa sistemas da Localiza.

Uso:
    python scripts/demo_f1.py [--base-url http://localhost:8000] [--token demo-admin] [--forbidden-token demo-support]

O token também pode vir de ARCHCORP_TOKEN (no modo público, a credencial configurada fora do Git) e a
URL de ARCHCORP_BASE_URL. Use `--forbidden-token ""` para pular a checagem de 403 (modo público).
Cada execução gera e-mail, ID legado e chaves novas; pode ser repetida no mesmo banco.
Código de saída: 0 se todas as checagens passarem, 1 se alguma falhar, 2 se a API estiver inacessível.
A indisponibilidade/timeout do CRM não tem chave de ativação na API; ela é coberta por
`tests/test_f1_cliente_reserva_contrato.py::test_f1_indisponibilidade_do_crm_retorna_erro_rastreado_sem_efeito_parcial`.
"""
import argparse
import os
import sys
from datetime import date, timedelta
from uuid import UUID, uuid4

import httpx

CADASTRAL_FIELDS = {"name", "email", "customerName", "customerEmail", "eligible", "consentService", "active", "legacyId", "phone"}


class Demo:
    def __init__(self, client: httpx.Client, token: str):
        self.client = client
        self.token = token
        self.passed = 0
        self.failed: list[str] = []

    def call(self, method: str, path: str, correlation_id: str, *, key: str | None = None, json=None, token: str | None = None) -> httpx.Response:
        headers = {"X-Correlation-ID": correlation_id}
        token = self.token if token is None else token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if key:
            headers["Idempotency-Key"] = key
        return self.client.request(method, path, headers=headers, json=json)

    def check(self, step: str, response: httpx.Response | None, conditions: list[tuple[str, bool]], detail: str = "") -> bool:
        correlation = response.headers.get("X-Correlation-ID", "-") if response is not None else "-"
        status = response.status_code if response is not None else "-"
        failures = [label for label, ok in conditions if not ok]
        mark = "OK  " if not failures else "FALHA"
        print(f"[{mark}] {step} | HTTP {status} | correlationId={correlation}")
        if detail:
            print(f"        {detail}")
        for label in failures:
            print(f"        esperado: {label}")
        if failures and response is not None:
            print(f"        resposta: {response.text[:400]}")
        if failures:
            self.failed.append(step)
        else:
            self.passed += 1
        return not failures

    def problem(self, step: str, response: httpx.Response, status: int, code: str, correlation_id: str) -> bool:
        body = safe_json(response)
        return self.check(step, response, [
            (f"status {status}", response.status_code == status),
            ("Content-Type application/problem+json", response.headers.get("content-type", "").startswith("application/problem+json")),
            (f"code {code}", body.get("code") == code),
            ("correlationId do corpo igual ao enviado", body.get("correlationId") == correlation_id == response.headers.get("X-Correlation-ID")),
        ], f"code={body.get('code')} detail={summarize(body.get('detail'))}")


def safe_json(response: httpx.Response) -> dict:
    try:
        value = response.json()
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {"_list": value}


def summarize(detail) -> str:
    if isinstance(detail, list):
        return "; ".join(f"{'.'.join(str(p) for p in e.get('loc', []))}: {e.get('msg')}" for e in detail)
    return str(detail)


def is_uuid(value) -> bool:
    try:
        UUID(str(value))
        return True
    except ValueError:
        return False


def run(demo: Demo, forbidden_token: str) -> None:
    run_id = uuid4().hex[:8]
    flow = str(uuid4())
    starts, ends = (date.today() + timedelta(days=7)).isoformat(), (date.today() + timedelta(days=10)).isoformat()
    print(f"== F1 caminho principal (execução {run_id}) | correlationId do fluxo={flow}")

    ready = demo.client.get("/health/ready")
    demo.check("0. API pronta (/health/ready)", ready, [("status UP e banco UP", safe_json(ready) == {"status": "UP", "database": "UP"})])

    created = demo.call("POST", "/api/v1/crm/customers", flow, json={
        "name": f"Cliente Sintético F1 {run_id}", "email": f"f1-{run_id}@cliente-sintetico.example.com", "legacyId": f"SINT-F1-{run_id}",
    })
    customer = safe_json(created)
    customer_id = customer.get("customerId")
    if not demo.check("1. CRM cadastra o cliente oficial", created, [("201", created.status_code == 201), ("customerId UUID", is_uuid(customer_id))],
                      f"customerId={customer_id} legacyId={customer.get('legacyId')}"):
        return

    official = demo.call("GET", f"/api/v1/crm/customers/{customer_id}", flow)
    demo.check("2. CRM devolve o cadastro (fonte oficial)", official, [("200", official.status_code == 200), ("mesmo nome e e-mail", safe_json(official).get("email") == customer["email"])],
               f"name={customer['name']!r} email={customer['email']}")

    body = {"customerId": customer_id, "vehicleGroup": "SUV-COMPACTO", "protectionCode": "BASICA", "serviceCode": "RENTAL-FLEX",
            "startsOn": starts, "endsOn": ends, "amount": 750.00, "currency": "BRL", "billingCycle": "ONCE", "slaHours": 8}
    reservation_key = f"demo-f1-res-{run_id}"
    reserved = demo.call("POST", "/api/v1/contracts/reservations", flow, key=reservation_key, json=body)
    reservation = safe_json(reserved)
    reservation_id = reservation.get("reservationId")
    if not demo.check("3. Reserva referencia só o customerId (sem dados cadastrais no corpo)", reserved, [
        ("201", reserved.status_code == 201), ("corpo sem campos cadastrais", CADASTRAL_FIELDS.isdisjoint(body)),
        ("mesmo customerId", reservation.get("customerId") == customer_id), ("status REQUESTED", reservation.get("status") == "REQUESTED"),
    ], f"reservationId={reservation_id} campos enviados={sorted(body)}"):
        return

    replay = demo.call("POST", "/api/v1/contracts/reservations", flow, key=reservation_key, json=body)
    demo.check("4. Repetição da reserva com a mesma Idempotency-Key", replay, [
        ("Idempotency-Replayed true", replay.headers.get("Idempotency-Replayed") == "true"),
        ("mesmo reservationId", safe_json(replay).get("reservationId") == reservation_id),
    ])

    draft_key = f"demo-f1-draft-{run_id}"
    draft_path = f"/api/v1/contracts/reservations/{reservation_id}/draft"
    drafted = demo.call("POST", draft_path, flow, key=draft_key)
    contract = safe_json(drafted).get("contract", {})
    contract_id = contract.get("contractId")
    if not demo.check("5. Rascunho gerado a partir da reserva, sem corpo e sem recadastro", drafted, [
        ("200", drafted.status_code == 200), ("Idempotency-Replayed false", drafted.headers.get("Idempotency-Replayed") == "false"),
        ("status DRAFT", contract.get("status") == "DRAFT"), ("customerId do CRM", contract.get("customerId") == customer_id),
        ("período da reserva", (contract.get("startsOn"), contract.get("endsOn")) == (starts, ends)),
        ("cobrança da reserva", contract.get("billing") == {"amount": 750.0, "currency": "BRL", "cycle": "ONCE"}),
    ], f"contractId={contract_id} customerId={contract.get('customerId')}"):
        return

    again = demo.call("POST", draft_path, flow, key=draft_key)
    demo.check("6. Repetição do rascunho com a mesma Idempotency-Key", again, [
        ("Idempotency-Replayed true", again.headers.get("Idempotency-Replayed") == "true"),
        ("mesmo contractId", safe_json(again).get("contract", {}).get("contractId") == contract_id),
    ])

    linked = demo.call("GET", f"/api/v1/contracts/reservations/{reservation_id}", flow)
    demo.check("7. Reserva vinculada ao contrato", linked, [
        ("status DRAFTED", safe_json(linked).get("status") == "DRAFTED"), ("contractId vinculado", safe_json(linked).get("contractId") == contract_id),
    ])

    contracts = demo.call("GET", f"/api/v1/contracts?customerId={customer_id}", flow)
    demo.check("8. Um único contrato para o cliente", contracts, [("1 contrato", [c.get("contractId") for c in safe_json(contracts).get("_list", [])] == [contract_id])])

    legacy = demo.call("GET", f"/api/v1/integration/legacy-ids/CRM/{customer['legacyId']}", flow)
    demo.check("9. ID legado do CRM resolve o mesmo UUID global", legacy, [("globalId = customerId do contrato", safe_json(legacy).get("globalId") == contract.get("customerId"))],
               f"CRM/{customer['legacyId']} -> {safe_json(legacy).get('globalId')}")

    trace = demo.call("GET", f"/api/v1/operations/{flow}", flow)
    steps = [(a.get("module"), a.get("operation"), a.get("entityId")) for a in safe_json(trace).get("audit", [])]
    expected = [("crm", "create_customer", customer_id), ("contracts", "create_reservation", reservation_id),
                ("contracts", "create_draft", contract_id), ("contracts", "draft_from_reservation", reservation_id)]
    demo.check("10. Trilha por correlação mostra cada etapa do F1", trace, [(f"auditoria {m}.{o}", (m, o, e) in steps) for m, o, e in expected],
               "auditoria: " + ", ".join(f"{m}.{o}" for m, o, _ in steps))

    print("== F1 ramificações (cada checagem usa um correlationId próprio)")
    cid = str(uuid4())
    invalid = demo.call("POST", "/api/v1/contracts/drafts", cid, key=f"demo-f1-invalid-{run_id}", json={
        "customerId": customer_id, "serviceCode": "RENTAL-FLEX", "startsOn": starts, "billing": {"amount": 0, "currency": "brl", "cycle": "MONTHLY"}})
    demo.problem("11. Validação estrutural: valor zero e moeda minúscula -> 422", invalid, 422, "VALIDATION_ERROR", cid)

    cid = str(uuid4())
    missing = demo.call("POST", "/api/v1/contracts/drafts", cid, key=f"demo-f1-missing-{run_id}", json={
        "customerId": str(uuid4()), "serviceCode": "RENTAL-FLEX", "startsOn": starts, "billing": {"amount": 100, "currency": "BRL", "cycle": "MONTHLY"}})
    demo.problem("12. Cliente inexistente no CRM -> 422", missing, 422, "BUSINESS_RULE_VIOLATION", cid)

    cid = str(uuid4())
    other = safe_json(demo.call("POST", "/api/v1/crm/customers", cid, json={"name": f"Cliente Inativo F1 {run_id}", "email": f"f1-inativo-{run_id}@cliente-sintetico.example.com"}))
    other_reservation = safe_json(demo.call("POST", "/api/v1/contracts/reservations", cid, json={**body, "customerId": other.get("customerId")}))
    demo.call("POST", f"/api/v1/crm/customers/{other.get('customerId')}/deactivate", cid)
    inactive = demo.call("POST", f"/api/v1/contracts/reservations/{other_reservation.get('reservationId')}/draft", cid, key=f"demo-f1-inactive-{run_id}")
    demo.problem("13. Cliente inativado no CRM após a reserva -> 422", inactive, 422, "BUSINESS_RULE_VIOLATION", cid)

    cid = str(uuid4())
    second = safe_json(demo.call("POST", "/api/v1/contracts/reservations", cid, json={**body, "vehicleGroup": "SEDAN-EXECUTIVO"}))
    reused = demo.call("POST", f"/api/v1/contracts/reservations/{second.get('reservationId')}/draft", cid, key=draft_key)
    demo.problem("14. Mesma Idempotency-Key em outra reserva -> 409", reused, 409, "IDEMPOTENCY_CONFLICT", cid)
    demo.call("POST", f"/api/v1/contracts/reservations/{second.get('reservationId')}/cancel", cid)
    kept = demo.call("GET", f"/api/v1/contracts/{contract_id}", cid)
    demo.check("15. Contrato da primeira reserva permanece DRAFT", kept, [("status DRAFT", safe_json(kept).get("status") == "DRAFT")])

    cid = str(uuid4())
    demo.problem("16. Sem credencial -> 401", demo.call("POST", draft_path, cid, key="demo-f1-auth", token=""), 401, "UNAUTHORIZED", cid)
    if forbidden_token:
        cid = str(uuid4())
        demo.problem("17. Papel sem permissão -> 403", demo.call("POST", draft_path, cid, key="demo-f1-auth", token=forbidden_token), 403, "FORBIDDEN", cid)
    else:
        print("[PULO] 17. Papel sem permissão -> 403 (sem --forbidden-token)")

    bad = demo.client.post(draft_path, headers={"Authorization": f"Bearer {demo.token}", "Idempotency-Key": "demo-f1-bad", "X-Correlation-ID": "nao-uuid"})
    body_bad = safe_json(bad)
    demo.check("18. X-Correlation-ID inválido -> 400 com UUID gerado", bad, [
        ("400 problem+json", bad.status_code == 400 and bad.headers.get("content-type", "").startswith("application/problem+json")),
        ("correlationId gerado é UUID e igual ao cabeçalho", is_uuid(body_bad.get("correlationId")) and body_bad.get("correlationId") == bad.headers.get("X-Correlation-ID")),
    ])

    print(f"== Resumo: cliente={customer_id} reserva={reservation_id} contrato={contract_id} correlationId={flow}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Demonstração verificável do F1 contra a API local.")
    parser.add_argument("--base-url", default=os.environ.get("ARCHCORP_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--token", default=os.environ.get("ARCHCORP_TOKEN", "demo-admin"))
    parser.add_argument("--forbidden-token", default="demo-support", help="token sem papel comercial/contratos; vazio pula a checagem de 403")
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
