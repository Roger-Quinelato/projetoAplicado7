import os
import statistics
import time

os.environ.setdefault("DATABASE_URL", "sqlite:///./tmp/performance-archcorp.db")

from fastapi.testclient import TestClient

from archcorp.infrastructure.db import Base, engine
from archcorp.main import app


Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
samples = []
with TestClient(app) as client:
    for _ in range(200):
        started = time.perf_counter()
        response = client.get("/health/ready")
        response.raise_for_status()
        samples.append((time.perf_counter() - started) * 1000)

p95 = statistics.quantiles(samples, n=100, method="inclusive")[94]
print(f"amostras={len(samples)} p95_ms={p95:.2f} meta_ms=500 resultado={'PASS' if p95 < 500 else 'FAIL'}")
raise SystemExit(0 if p95 < 500 else 1)
