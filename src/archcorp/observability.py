import json
import logging
import time
from collections import defaultdict
from contextvars import ContextVar

from fastapi import Request, Response


correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="unknown")
COUNTERS: dict[str, int] = defaultdict(int)
LATENCY_SUM: dict[str, float] = defaultdict(float)
# Limites (s) do histograma de latência: permitem estimar p95 por operação a partir de /metrics.
LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
LATENCY_HISTOGRAM: dict[str, list[int]] = defaultdict(lambda: [0] * (len(LATENCY_BUCKETS) + 1))
# Séries separadas de COUNTERS: códigos de erro e replays têm cardinalidade fixa e própria.
PROBLEMS: dict[tuple[int, str], int] = defaultdict(int)
IDEMPOTENCY_REPLAYS: dict[str, int] = defaultdict(int)


class JsonFormatter(logging.Formatter):
    # O sufixo Z do timestamp declara UTC; sem isto o horário sairia no fuso local.
    converter = time.gmtime

    def format(self, record: logging.LogRecord) -> str:
        """Formata o registro de log como JSON com correlationId, operação e resultado."""
        return json.dumps({
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "module": record.name,
            "operation": getattr(record, "operation", record.funcName),
            "correlationId": getattr(record, "correlationId", correlation_id_var.get()),
            "result": getattr(record, "result", "recorded"),
            "message": record.getMessage(),
            **{field: getattr(record, field) for field in ("eventId", "errorType") if hasattr(record, field)},
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
    elapsed = time.perf_counter() - started
    operation = escape_label(operation_label(request))
    COUNTERS[f"requests_total{{operation=\"{operation}\",status=\"{response.status_code}\"}}"] += 1
    LATENCY_SUM[operation] += elapsed
    histogram = LATENCY_HISTOGRAM[operation]
    histogram[next((index for index, limit in enumerate(LATENCY_BUCKETS) if elapsed <= limit), len(LATENCY_BUCKETS))] += 1
    return response


def record_problem(status: int, code: str) -> None:
    """Conta respostas problem+json por status e código de negócio."""
    PROBLEMS[(status, code)] += 1


def record_idempotency_replay(operation: str) -> None:
    """Conta respostas recuperadas por Idempotency-Key (proxy de repetição após falha ambígua)."""
    IDEMPOTENCY_REPLAYS[operation] += 1


def render_metrics() -> str:
    """Renderiza os contadores no formato de texto do Prometheus."""
    lines = ["# HELP archcorp_requests_total Total de requisições", "# TYPE archcorp_requests_total counter"]
    lines.extend(f"archcorp_{key} {value}" for key, value in sorted(COUNTERS.items()))
    lines.extend(f'archcorp_request_latency_seconds_sum{{operation="{key}"}} {value:.6f}' for key, value in sorted(LATENCY_SUM.items()))
    lines += ["# HELP archcorp_request_latency_seconds Latência das requisições por operação",
              "# TYPE archcorp_request_latency_seconds histogram"]
    for operation, counts in sorted(LATENCY_HISTOGRAM.items()):
        cumulative = 0
        for limit, count in zip((*LATENCY_BUCKETS, "+Inf"), counts):
            cumulative += count
            lines.append(f'archcorp_request_latency_seconds_bucket{{operation="{operation}",le="{limit}"}} {cumulative}')
        lines.append(f'archcorp_request_latency_seconds_count{{operation="{operation}"}} {cumulative}')
    lines += ["# HELP archcorp_problems_total Respostas de erro por status e código", "# TYPE archcorp_problems_total counter"]
    lines.extend(f'archcorp_problems_total{{status="{status}",code="{escape_label(code)}"}} {value}'
                 for (status, code), value in sorted(PROBLEMS.items()))
    lines += ["# HELP archcorp_idempotency_replays_total Respostas recuperadas por Idempotency-Key",
              "# TYPE archcorp_idempotency_replays_total counter"]
    lines.extend(f'archcorp_idempotency_replays_total{{operation="{escape_label(key)}"}} {value}'
                 for key, value in sorted(IDEMPOTENCY_REPLAYS.items()))
    return "\n".join(lines) + "\n"
