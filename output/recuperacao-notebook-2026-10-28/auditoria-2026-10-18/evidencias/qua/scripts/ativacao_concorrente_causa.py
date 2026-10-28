"""F-QUA - QUA-13: qual excecao produz o HTTP 500 na ativacao concorrente? (execucao in-process)

Uso: python -I ativacao_concorrente_causa.py <ISO>\\src <RODADAS>   (com cwd = <ISO>, banco SQLite da copia)

Os logs do servidor nao trazem o tipo da excecao (QUA-01). Este script reproduz o cenário de
ativacao_concorrente_api.py com a aplicacao em processo (TestClient) e captura o exc_info dos
registros do logger 'archcorp' emitidos pelo middleware de main.py:102-104, sem alterar o codigo.
"""
import logging
import sys
import threading
import uuid
from collections import Counter

sys.path.insert(0, sys.argv[1])
ROUNDS = int(sys.argv[2])

from fastapi.testclient import TestClient  # noqa: E402

from archcorp.main import app  # noqa: E402
from archcorp.observability import logger  # noqa: E402

captured: list[str] = []


class Capture(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        if record.exc_info and record.exc_info[0] is not None:
            captured.append(f"{record.exc_info[0].__name__}: {str(record.exc_info[1])[:140]}")


logger.addHandler(Capture())
logger.propagate = False
outcome: Counter = Counter()

with TestClient(app, headers={"Authorization": "Bearer demo-admin"}) as client:
    for _ in range(ROUNDS):
        correlation = str(uuid.uuid4())
        headers = {"X-Correlation-ID": correlation}
        customer = client.post("/api/v1/crm/customers", headers=headers, json={
            "name": "Causa Sintetica", "email": f"causa-{uuid.uuid4().hex}@example.com"}).json()
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
        outcome[tuple(sorted(codes))] += 1

print(f"codigos HTTP por rodada: {dict(outcome)}")
print("excecoes capturadas pelo middleware (tipo: mensagem), contagem:")
for name, count in Counter(captured).most_common():
    print(f"  {count}x {name}")
