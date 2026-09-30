"""Carga idempotente de dados sintéticos pela API pública (docs/DADOS_SINTETICOS.md).

Uso local, na mesma base configurada em DATABASE_URL:
    PYTHONPATH=src python scripts/seed_sintetico.py
Uso contra uma API em execução:
    PYTHONPATH=src python scripts/seed_sintetico.py --base-url http://localhost:8000 --token demo-admin

Executar mais de uma vez não duplica registros: clientes são localizados pelo
identificador legado sintético e rascunhos usam Idempotency-Key fixa.
"""
import argparse
import json
from contextlib import contextmanager

CUSTOMERS = [
    {"legacyId": "SINT-CLI-001", "name": "Transportes Aurora Sintética Ltda.", "email": "frota@aurora-sintetica.example.com",
     "eligible": True, "consentService": True},
    {"legacyId": "SINT-CLI-002", "name": "Construtora Horizonte Fictícia S.A.", "email": "gestao@horizonte-ficticia.example.net",
     "eligible": True, "consentService": True},
    {"legacyId": "SINT-CLI-003", "name": "Comércio Sem Consentimento Demo", "email": "contato@sem-consentimento.example.org",
     "eligible": True, "consentService": False},
]
DRAFTS = [
    {"legacyId": "SINT-CLI-001", "key": "seed-draft-aurora", "serviceCode": "RENTAL-FLEX", "startsOn": "2027-01-04",
     "billing": {"amount": 2500.00, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8},
    {"legacyId": "SINT-CLI-002", "key": "seed-draft-horizonte", "serviceCode": "RENTAL-FLEX", "startsOn": "2027-02-01",
     "billing": {"amount": 4100.00, "currency": "BRL", "cycle": "QUARTERLY"}, "slaHours": 4},
]


@contextmanager
def api_client(base_url: str | None):
    """Abre um cliente HTTP para a URL informada ou, sem ela, para a aplicação em processo."""
    if base_url:
        import httpx
        with httpx.Client(base_url=base_url, timeout=10) as client:
            yield client
    else:
        from fastapi.testclient import TestClient
        from archcorp.main import app
        with TestClient(app) as client:
            yield client


def seed(client, token: str) -> dict:
    """Cria clientes e rascunhos sintéticos pela API; execuções repetidas não duplicam registros."""
    headers = {"Authorization": f"Bearer {token}"}
    customers: dict[str, str] = {}
    created = 0
    for item in CUSTOMERS:
        found = client.get(f"/api/v1/integration/legacy-ids/CRM/{item['legacyId']}", headers=headers)
        if found.status_code == 200:
            customers[item["legacyId"]] = found.json()["globalId"]
            continue
        if found.status_code != 404:
            found.raise_for_status()
        response = client.post("/api/v1/crm/customers", headers=headers, json=item)
        response.raise_for_status()
        customers[item["legacyId"]] = response.json()["customerId"]
        created += 1
    contracts = {}
    for draft in DRAFTS:
        body = {key: value for key, value in draft.items() if key not in {"legacyId", "key"}}
        body["customerId"] = customers[draft["legacyId"]]
        response = client.post("/api/v1/contracts/drafts", headers={**headers, "Idempotency-Key": draft["key"]}, json=body)
        response.raise_for_status()
        contracts[draft["key"]] = response.json()["contractId"]
    return {"customersCreated": created, "customers": customers, "contracts": contracts}


def main() -> None:
    """Lê os argumentos da linha de comando e imprime o resultado da carga em JSON."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", help="URL da API; sem ela, usa a aplicação em processo")
    parser.add_argument("--token", default="demo-admin", help="Token com papel admin")
    args = parser.parse_args()
    with api_client(args.base_url) as client:
        print(json.dumps(seed(client, args.token), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
