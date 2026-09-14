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


async def metrics_middleware(request: Request, call_next):
    started = time.perf_counter()
    response: Response = await call_next(request)
    operation = f"{request.method}_{request.url.path}"
    COUNTERS[f"requests_total{{operation=\"{operation}\",status=\"{response.status_code}\"}}"] += 1
    LATENCY_SUM[operation] += time.perf_counter() - started
    return response


def render_metrics() -> str:
    lines = ["# HELP archcorp_requests_total Total de requisições", "# TYPE archcorp_requests_total counter"]
    lines.extend(f"archcorp_{key} {value}" for key, value in sorted(COUNTERS.items()))
    lines.extend(f'archcorp_request_latency_seconds_sum{{operation="{key}"}} {value:.6f}' for key, value in sorted(LATENCY_SUM.items()))
    return "\n".join(lines) + "\n"
