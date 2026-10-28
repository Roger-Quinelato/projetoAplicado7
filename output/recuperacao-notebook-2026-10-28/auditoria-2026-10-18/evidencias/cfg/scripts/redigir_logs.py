"""Redige credenciais conhecidas nas saídas brutas da frente F-CFG (logs/).

Uso: PY -I redigir_logs.py <LOGS>

Substitui por <REDACTED> as cadeias de credencial de desenvolvimento e de CI que aparecem nos
logs (não são segredos de produção, mas o registro não copia valores). Não altera conteúdo
além disso. Relê cada arquivo e reporta quantas substituições fez.
"""
import sys
from pathlib import Path

LOGS = Path(sys.argv[1]).resolve()
PADROES = [
    "synthetic-ci-only",
    "guest:guest",
    "archcorp:archcorp",
    "POSTGRES_PASSWORD=archcorp",
    "POSTGRES_PASSWORD=synthetic-ci-only",
]
total = 0
for arq in sorted(LOGS.glob("*.txt")) + sorted(LOGS.glob("*.json")):
    texto = arq.read_text(encoding="utf-8", errors="replace")
    novo = texto
    n = 0
    for padrao in PADROES:
        if padrao in novo:
            n += novo.count(padrao)
            alvo = padrao.split("=", 1)[1] if padrao.startswith("POSTGRES_PASSWORD=") else padrao
            novo = novo.replace(padrao, padrao.replace(alvo, "<REDACTED>"))
    if n:
        arq.write_text(novo, encoding="utf-8")
        total += n
        print(f"{arq.name}: {n} substituicao(oes)")
print(f"total de substituicoes: {total}")
