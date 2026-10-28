"""F-QUA - QUA-13 / AUD-10: duas ativacoes simultaneas do mesmo contrato com chaves diferentes.

Uso: python -I ativacao_concorrente_api.py http://127.0.0.1:18103 <TOKEN_ADMIN_LOCAL_DE_DEMONSTRACAO> <RODADAS>

Por rodada: cria cliente e rascunho sinteticos; dispara duas ativacoes ao mesmo tempo (barreira),
com Idempotency-Key diferentes e o mesmo X-Correlation-ID; conta os ContractActivated.v1 da
correlacao em GET /api/v1/operations/{correlationId}. Roda contra qualquer banco que a API use
(SQLite da copia aqui; PostgreSQL dedicado quando disponivel, sem alterar o codigo).
Resultado esperado pela regra de negocio (fluxo minimo 2 e RNF-02): um evento por contrato.
"""
import sys
import threading
import uuid
from collections import Counter

import httpx

BASE, TOKEN, ROUNDS = sys.argv[1], sys.argv[2], int(sys.argv[3])
client = httpx.Client(base_url=BASE, timeout=60, headers={"Authorization": f"Bearer {TOKEN}"})
outcome: Counter = Counter()

for round_number in range(ROUNDS):
    correlation = str(uuid.uuid4())
    headers = {"X-Correlation-ID": correlation}
    customer = client.post("/api/v1/crm/customers", headers=headers, json={
        "name": "Concorrencia Sintetica", "email": f"conc-{uuid.uuid4().hex}@example.com"}).json()
    draft = client.post("/api/v1/contracts/drafts", headers={**headers, "Idempotency-Key": str(uuid.uuid4())}, json={
        "customerId": customer["customerId"], "serviceCode": "RENTAL-FLEX", "startsOn": "2027-01-04",
        "billing": {"amount": 1200.0, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8}).json()
    contract_id = draft["contractId"]
    barrier = threading.Barrier(2)
    codes: list[int] = []

    def activate() -> None:
        barrier.wait(timeout=10)
        response = client.post(f"/api/v1/contracts/{contract_id}/activate",
                               headers={**headers, "Idempotency-Key": str(uuid.uuid4())})
        codes.append(response.status_code)

    threads = [threading.Thread(target=activate) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    trace = client.get(f"/api/v1/operations/{correlation}", headers=headers).json()
    events = sum(1 for event in trace["events"] if event["eventType"] == "ContractActivated.v1")
    outcome[(tuple(sorted(codes)), events)] += 1
    print(f"rodada {round_number + 1}: codigos={sorted(codes)} ContractActivated.v1={events}")

print("\nRESUMO (codigos HTTP, eventos ContractActivated.v1) -> rodadas")
for (codes, events), count in sorted(outcome.items()):
    print(f"  {codes} eventos={events}: {count}")
print(f"rodadas com mais de um evento: {sum(c for (_, e), c in outcome.items() if e > 1)} de {ROUNDS}")
