import json
import logging
import time
from collections import defaultdict
from contextvars import ContextVar

from fastapi import Request, Response


correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="unknown")
COUNTERS: dict[str, int] = defaultdict(int)
LATENCY_SUM: dict[str, float] = defaultdict(float)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        """Formata o registro de log como JSON com correlationId, operação e resultado."""
        return json.dumps({
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "module": record.name,
            "operation": getattr(record, "operation", record.funcName),
            "correlationId": correlation_id_var.get(),
            "result": getattr(record, "result", "recorded"),
            "message": record.getMessage(),
        }, ensure_ascii=False)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
logger = logging.getLogger("archcorp")


KNOWN_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})


def escape_label(value: str) -> str:
    """Escape de valor de rótulo no formato de texto do Prometheus."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def operation_label(request: Request) -> str:
    """Rótulo de cardinalidade limitada: método conhecido e template da rota.

    Usar o caminho recebido criaria uma série por URL (inclusive inexistente ou
    negada) e exporia identificadores nas métricas.
    """
    method = request.method if request.method in KNOWN_METHODS else "OTHER"
    route = request.scope.get("route")
    return f"{method}_{getattr(route, 'path', None) or 'unmatched'}"


async def metrics_middleware(request: Request, call_next):
    """Conta requisições por operação e status e acumula a latência."""
    started = time.perf_counter()
    response: Response = await call_next(request)
    operation = escape_label(operation_label(request))
    COUNTERS[f"requests_total{{operation=\"{operation}\",status=\"{response.status_code}\"}}"] += 1
    LATENCY_SUM[operation] += time.perf_counter() - started
    return response


def render_metrics() -> str:
    """Renderiza os contadores no formato de texto do Prometheus."""
    lines = ["# HELP archcorp_requests_total Total de requisições", "# TYPE archcorp_requests_total counter"]
    lines.extend(f"archcorp_{key} {value}" for key, value in sorted(COUNTERS.items()))
    lines.extend(f'archcorp_request_latency_seconds_sum{{operation="{key}"}} {value:.6f}' for key, value in sorted(LATENCY_SUM.items()))
    return "\n".join(lines) + "\n"
