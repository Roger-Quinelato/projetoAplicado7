"""E-07 (AUD-01, AUD-12, AUD-31): evento venenoso e reprocessamento (SQLite executado).

A) consumidor que audita e depois levanta exceção Python;
B) consumidor que audita e depois provoca erro de banco real (NOT NULL -> IntegrityError);
C) faturamento final sem fatura inicial (regra real de Finance, pelo despachante de produção);
D) ContractActivated.v1 com '1e20': o SQLite aceita (limite do SQLite; o PostgreSQL recusa com DataError em 01/10).
PostgreSQL (NÃO executado localmente): ADB_URL=... (banco descartável). Em PG, o cenário D deve falhar com DataError.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

from dad_common import CID, H, reset_db, rows, scalar, setup

setup("e07.db")
from fastapi.testclient import TestClient  # noqa: E402

from archcorp.config import settings  # noqa: E402
from archcorp.infrastructure.db import SessionLocal  # noqa: E402
from archcorp.integration.models import InboxEvent, OutboxEvent  # noqa: E402
from archcorp.integration.service import EventDispatcher, audit  # noqa: E402
from archcorp.main import app, dispatcher as real  # noqa: E402

T0 = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)


def consumidor_saudavel(rotulo):
    def handler(session, env):
        audit(session, env["correlationId"], "test", f"saudavel-{rotulo}", "success")
    return handler


def venenoso_python(session, env):
    audit(session, env["correlationId"], "test", "venenoso-python", "success")
    session.flush()
    raise RuntimeError("falha de regra sintética")


def venenoso_banco(session, env):
    audit(session, env["correlationId"], "test", "venenoso-banco", "success")
    session.flush()
    session.add(InboxEvent(event_id=None, consumer="venenoso-banco"))  # NOT NULL -> IntegrityError
    session.flush()


def cenario(rotulo, tipo_veneno, tipo_saudavel, handler_veneno, handler_saudavel, operacao_veneno, operacao_saudavel):
    despachante = EventDispatcher({tipo_veneno: [(f"veneno-{rotulo}", handler_veneno)],
                                   tipo_saudavel: [(f"saudavel-{rotulo}", handler_saudavel)]})
    with SessionLocal() as s:
        veneno = OutboxEvent(event_type=tipo_veneno, producer="test", payload={}, correlation_id=CID, occurred_at=T0)
        saudavel = OutboxEvent(event_type=tipo_saudavel, producer="test", payload={},
                               correlation_id=str(uuid.uuid4()), occurred_at=T0 + timedelta(seconds=1))
        s.add_all([veneno, saudavel])
        s.commit()
        vid, sid = veneno.event_id, saudavel.event_id
    for ciclo in range(settings.retry_limit + 1):
        with SessionLocal() as s:
            resultado = despachante.dispatch_pending(s)
            v = s.get(OutboxEvent, vid)
            h = s.get(OutboxEvent, sid)
            print(f"[{rotulo}] ciclo {ciclo + 1}: {resultado} | veneno={v.status}/tentativas={v.attempts} "
                  f"| saudavel={h.status}")
    with SessionLocal() as s:
        print(f"[{rotulo}] motivo gravado: '{s.get(OutboxEvent, vid).last_error}'")
    print(f"[{rotulo}] auditoria do veneno gravada="
          f"{scalar('SELECT count(*) FROM integration_audit WHERE operation = :op', op=operacao_veneno)}"
          f" | inbox do veneno={scalar('SELECT count(*) FROM integration_inbox WHERE event_id = :e', e=vid)}"
          f" | auditoria saudável={scalar('SELECT count(*) FROM integration_audit WHERE operation = :op', op=operacao_saudavel)}")


def cenario_real(rotulo, tipo, payload, ciclos):
    with SessionLocal() as s:
        ev = OutboxEvent(event_type=tipo, producer="test", payload=payload, correlation_id=CID, occurred_at=T0)
        s.add(ev)
        s.commit()
        eid = ev.event_id
    for ciclo in range(ciclos):
        with SessionLocal() as s:
            print(f"[{rotulo}] ciclo {ciclo + 1}: {real.dispatch_pending(s)}")
    with SessionLocal() as s:
        e = s.get(OutboxEvent, eid)
        print(f"[{rotulo}] status={e.status} tentativas={e.attempts} motivo='{e.last_error}'")
    return eid


def payload_fechamento():
    return {"contractId": str(uuid.uuid4()), "customerId": str(uuid.uuid4()), "serviceCode": "RENTAL-FLEX",
            "startsOn": "2026-10-01", "endsOn": "2026-12-01",
            "billing": {"amount": 100, "currency": "BRL", "cycle": "MONTHLY"}, "slaHours": 8,
            "status": "CLOSED", "closeReason": "teste"}


def payload_ativacao(valor):
    return {"contractId": str(uuid.uuid4()), "customerId": str(uuid.uuid4()), "serviceCode": "RENTAL-FLEX",
            "startsOn": "2026-10-01", "billing": {"amount": valor, "currency": "BRL", "cycle": "MONTHLY"},
            "slaHours": 8, "status": "ACTIVE"}


if os.environ.get("ADB_URL"):
    reset_db()
with TestClient(app, raise_server_exceptions=False) as c:
    cenario("A python", "VenenoPy.v1", "SaudavelA.v1", venenoso_python, consumidor_saudavel("A"),
            "venenoso-python", "saudavel-A")
    cenario("B banco", "VenenoBd.v1", "SaudavelB.v1", venenoso_banco, consumidor_saudavel("B"),
            "venenoso-banco", "saudavel-B")
    cenario_real("C fatura final sem inicial", "ContractClosed.v1", payload_fechamento(), settings.retry_limit)
    cenario_real("D valor 1e20 (SQLite aceita)", "ContractActivated.v1", payload_ativacao("1e20"), 1)
    print("valores gravados acima de 1e12:", rows("SELECT amount, status FROM finance_invoices WHERE amount > 1000000000000"))
    falhas = c.get("/api/v1/integration/failures", headers=H).json()
    print("falhas via API:", [(f["eventType"], f["attempts"], f["reason"][:45]) for f in falhas])
    r = c.post(f"/api/v1/integration/failures/{falhas[0]['eventId']}/reprocess", headers=H)
    print("reprocessamento:", r.status_code, r.json())
    print("auditoria do reprocessamento (operation, details):",
          rows("SELECT operation, details FROM integration_audit WHERE operation = 'reprocess_event'"))
