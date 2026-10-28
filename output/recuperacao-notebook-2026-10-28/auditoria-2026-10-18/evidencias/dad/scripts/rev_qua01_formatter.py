"""Revisão cruzada de QUA-01 (independente): o JsonFormatter registra tipo ou pilha de logger.exception? SQLite, sem banco."""
import json
import logging

from dad_common import setup

setup("rev_qua01.db")
from archcorp.observability import JsonFormatter, logger  # noqa: E402

capturados = []


class Captura(logging.Handler):
    def emit(self, record):
        capturados.append(JsonFormatter().format(record))


cap = Captura()
logger.addHandler(cap)
try:
    raise ValueError("falha sintética de regra")
except ValueError:
    logger.exception("Erro não tratado", extra={"operation": "/api/v1/teste", "result": "failure"})
logger.removeHandler(cap)
saida = capturados[0]
dados = json.loads(saida)
print("chaves do JSON:", sorted(dados))
print("exception:", "exception" in dados, "| errorType:", "errorType" in dados,
      "| 'Traceback' no texto:", "Traceback" in saida, "| 'ValueError' no texto:", "ValueError" in saida)
print("module:", dados["module"], "| operation:", dados["operation"])
