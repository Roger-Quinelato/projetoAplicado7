"""F-QUA - AUD-32: o JsonFormatter de producao registra o tipo e a pilha de uma excecao?

Uso (copia isolada iso-qua, Python do venv-auditoria, modo isolado):
    python -I experimento_formatter_excecao.py <ISO>\\src

Reproduz dois padroes reais de registro do codigo:
  A) main.py:102-104 - logger.exception("Erro nao tratado") dentro de um except, sem errorType.
  B) integration/service.py:105-106 - logger.warning com extra errorType=type(exc).__name__.
Cada registro capturado no logger "archcorp" e formatado com JsonFormatter (observability.py),
o mesmo formatter ligado ao StreamHandler da aplicacao.
"""
import logging
import sys

sys.path.insert(0, sys.argv[1])

from archcorp.observability import JsonFormatter, logger  # noqa: E402

captured: list[logging.LogRecord] = []


class Capture(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        captured.append(record)


logger.addHandler(Capture())
logger.propagate = False  # so o experimento; a saida da aplicacao nao e duplicada


def caso_a_middleware() -> None:
    try:
        raise ValueError("falha sintetica do caso A")
    except Exception:
        logger.exception("Erro não tratado", extra={"operation": "/api/v1/sintetico", "result": "failure"})


def caso_b_despacho() -> None:
    try:
        raise RuntimeError("falha sintetica do caso B")
    except Exception as exc:
        logger.warning("Falha ao despachar evento", extra={
            "operation": "dispatch_event", "result": "failure",
            "eventId": "00000000-0000-4000-8000-000000000000",
            "correlationId": "11111111-1111-4111-8111-111111111111",
            "errorType": type(exc).__name__,
        })


caso_a_middleware()
caso_b_despacho()

for name, record in zip(("A_middleware_logger_exception", "B_despacho_errorType"), captured):
    line = JsonFormatter().format(record)
    print(f"== caso {name}")
    print(line)
    print(f"  record.exc_info preenchido: {record.exc_info is not None}")
    print(f"  tipo da excecao ('ValueError'/'RuntimeError') na saida: {'ValueError' in line or 'RuntimeError' in line}")
    print(f"  pilha ('Traceback') na saida: {'Traceback' in line}")
    print(f"  chave 'exception' na saida: {'\"exception\"' in line}")
    print(f"  chave 'errorType' na saida: {'\"errorType\"' in line}")
