"""Utilitários dos roteiros da frente F-DAD (auditoria de 18/10/2026).

Variáveis de ambiente:
- DAD_ISO: cópia de execução (padrão: iso-dad). Toda escrita fica em <ISO>\\tmp.
- ADB_URL: banco ALTERNATIVO e DESCARTÁVEL (por exemplo PostgreSQL de teste). Quando definido, os roteiros
  apagam as tabelas desse banco antes de rodar. Nunca apontar para banco com dados reais.
"""
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

ISO = Path(os.environ.get("DAD_ISO", r"C:\Users\roger\.claude\jobs\f5019419\tmp\iso-dad"))
CID = "11111111-1111-4111-8111-111111111111"
H = {"Authorization": "Bearer demo-admin", "X-Correlation-ID": CID}


def setup(db_name: str) -> str:
    """Aponta DATABASE_URL para um SQLite descartável em <ISO>\\tmp (ou para ADB_URL) e prepara o import."""
    url = os.environ.get("ADB_URL")
    if not url:
        db = ISO / "tmp" / db_name
        db.parent.mkdir(parents=True, exist_ok=True)
        if db.exists():
            db.unlink()
        url = "sqlite:///" + db.as_posix()
    os.environ["DATABASE_URL"] = url
    os.environ.pop("RABBITMQ_URL", None)
    sys.path.insert(0, str(ISO / "src"))
    os.chdir(ISO)
    import logging

    logging.disable(logging.INFO)  # mantém WARNING/ERROR (falhas de despacho); corta o INFO de requisições
    return url


def reset_db() -> None:
    """Apaga as tabelas e o carimbo do Alembic. Só com banco descartável (ADB_URL)."""
    from archcorp.infrastructure.db import Base, engine

    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")


def customer(c, tag="cli"):
    body = {"name": "Empresa Sintética", "email": f"{tag}-{uuid4().hex[:10]}@example.com"}
    return c.post("/api/v1/crm/customers", headers=H, json=body).json()


def draft(c, cust, key, amount=2500, starts="2027-03-01", cycle="MONTHLY"):
    body = {"customerId": cust["customerId"], "serviceCode": "RENTAL-FLEX", "startsOn": starts,
            "billing": {"amount": amount, "currency": "BRL", "cycle": cycle}, "slaHours": 8}
    return c.post("/api/v1/contracts/drafts", headers={**H, "Idempotency-Key": key}, json=body)


def activate(c, contract_id, key):
    return c.post(f"/api/v1/contracts/{contract_id}/activate", headers={**H, "Idempotency-Key": key})


def dispatch(c):
    return c.post("/api/v1/integration/outbox/dispatch", headers=H).json()


def show(label, r):
    try:
        body = r.json()
    except ValueError:
        body = r.text
    text = json.dumps(body, ensure_ascii=False)[:260]
    print(f"[{label}] {r.request.method} {r.request.url.path} -> {r.status_code} "
          f"replay={r.headers.get('Idempotency-Replayed')} {text}")
    return body


def rows(sql, **params):
    from sqlalchemy import text

    from archcorp.infrastructure.db import engine

    with engine.connect() as conn:
        return [tuple(r) for r in conn.execute(text(sql), params).all()]


def scalar(sql, **params):
    result = rows(sql, **params)
    return result[0][0] if result else None
