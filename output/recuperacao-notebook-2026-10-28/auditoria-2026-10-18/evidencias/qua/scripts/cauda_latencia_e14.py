"""F-QUA - E-14 (complemento): caracteriza a cauda de latencia observada em medir_rotas_e14.py.

Uso: python -I cauda_latencia_e14.py http://127.0.0.1:18103 <TOKEN_ADMIN_LOCAL_DE_DEMONSTRACAO> <N>
Faz N leituras de /api/v1/crm/customers e N criacoes de cliente sintetico, sequenciais, e imprime
cada requisicao acima de 300 ms com o indice e o instante (segundos desde o inicio). Serve para
distinguir picos isolados de picos agrupados no tempo (instabilidade do ambiente).
"""
import sys
import time
import uuid

import httpx

BASE, TOKEN, N = sys.argv[1], sys.argv[2], int(sys.argv[3])
client = httpx.Client(base_url=BASE, timeout=60, headers={"Authorization": f"Bearer {TOKEN}"})
origin = time.perf_counter()
slow: list[str] = []
durations: list[float] = []
codes: dict[int, int] = {}

for label, method, url, body in [
    ("LEITURA customers", "GET", "/api/v1/crm/customers?limit=10&offset=0", None),
    ("ESCRITA customers", "POST", "/api/v1/crm/customers", "novo"),
]:
    for i in range(N):
        payload = None
        if body == "novo":
            payload = {"name": "E14 Cauda", "email": f"cauda-{uuid.uuid4().hex}@example.com"}
        started = time.perf_counter()
        response = client.request(method, url, json=payload)
        elapsed = (time.perf_counter() - started) * 1000
        durations.append(elapsed)
        codes[response.status_code] = codes.get(response.status_code, 0) + 1
        if elapsed > 300:
            slow.append(f"{label} #{i} {elapsed:.0f} ms em t={started - origin:.1f}s")

durations.sort()
print(f"total={len(durations)} codigos={codes}")
print(f"mediana={durations[len(durations) // 2]:.1f} ms p99={durations[int(len(durations) * 0.99) - 1]:.1f} ms max={durations[-1]:.1f} ms")
print(f"requisicoes acima de 300 ms: {len(slow)}")
for line in slow:
    print("  " + line)
