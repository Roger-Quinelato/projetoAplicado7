"""E-09 (AUD-39, AUD-41, Q-01 residual, data local em contracts): escopo da Idempotency-Key, prazo do ONBOARDING,
datas sem indicador UTC e data local no encerramento (SQLite executado)."""
from datetime import date, datetime, timezone

from dad_common import CID, H, activate, customer, dispatch, draft, setup, show

setup("e09.db")
from fastapi.testclient import TestClient  # noqa: E402

import archcorp.contracts.service as contratos  # noqa: E402
import archcorp.workflow.service as workflow  # noqa: E402
from archcorp.infrastructure.db import SessionLocal  # noqa: E402
from archcorp.integration.models import OutboxEvent  # noqa: E402
from archcorp.main import app  # noqa: E402

SUPORTE = {"Authorization": "Bearer demo-support", "X-Correlation-ID": CID}
UTC = timezone.utc

with TestClient(app, raise_server_exceptions=False) as c:
    print("== a) escopo da Idempotency-Key (chamados)")
    cust = customer(c, "chave")
    cid = draft(c, cust, "E09-D1").json()["contractId"]
    activate(c, cid, "E09-A1")
    dispatch(c)
    corpo = {"customerId": cust["customerId"], "contractId": cid, "serviceCode": "RENTAL-FLEX",
             "category": "OUTAGE", "description": "Falha sintética de energia"}
    show("admin abre chamado", c.post("/api/v1/support/tickets", headers={**H, "Idempotency-Key": "E09-K1"}, json=corpo))
    show("suporte repete chave e corpo", c.post("/api/v1/support/tickets", headers={**SUPORTE, "Idempotency-Key": "E09-K1"}, json=corpo))
    show("mesma chave, descrição diferente", c.post("/api/v1/support/tickets", headers={**H, "Idempotency-Key": "E09-K1"},
                                                    json={**corpo, "description": "Outra descrição sintética"}))

    print("== b) ONBOARDING: prazo de 72 h contado do despacho ou do evento")

    def onboarding(rotulo, despacho, ocorrido):
        cust_t = customer(c, "onb")
        cid_t = draft(c, cust_t, f"E09-OD-{rotulo}").json()["contractId"]
        eid = activate(c, cid_t, f"E09-OA-{rotulo}").json()["eventId"]
        with SessionLocal() as s:
            s.get(OutboxEvent, eid).occurred_at = ocorrido
            s.commit()

        class RelogioFixo(datetime):
            @classmethod
            def now(cls, tz=None):
                return despacho

        original = workflow.datetime
        workflow.datetime = RelogioFixo
        try:
            resumo = dispatch(c)
        finally:
            workflow.datetime = original
        processo = next(p for p in c.get("/api/v1/workflow/processes", headers=H).json() if p["referenceId"] == cid_t)
        print(f"[ONBOARDING {rotulo}] occurredAt={ocorrido.isoformat()} despacho={despacho.isoformat()} "
              f"resumo={resumo} dueAt={processo['dueAt']}")

    onboarding("sem atraso", datetime(2026, 10, 19, 10, 0, tzinfo=UTC), datetime(2026, 10, 19, 10, 0, tzinfo=UTC))
    onboarding("atraso de 10 h", datetime(2026, 10, 19, 20, 0, tzinfo=UTC), datetime(2026, 10, 19, 10, 0, tzinfo=UTC))

    print("== c) datas sem indicador de fuso em respostas (SQLite devolve datetime sem tzinfo)")
    tickets_api = c.get("/api/v1/support/tickets", headers=H).json()
    print("  support dueAt (serviço usa iso_utc):", [t["dueAt"] for t in tickets_api][:2])
    ops = c.get("/api/v1/operations/" + CID, headers=H).json()
    print("  operations audit.occurredAt (sem tratamento de fuso):", [a["occurredAt"] for a in ops["audit"]][:2])
    procs = c.get("/api/v1/workflow/processes", headers=H).json()
    print("  workflow processes (processType, dueAt, sem tratamento de fuso):", [(p["processType"], p["dueAt"]) for p in procs])

    print("== d) encerramento sem endsOn usa date.today() (relógio local), não a data UTC")

    class DataLocal(date):
        @classmethod
        def today(cls):
            return date(2026, 10, 18)

    cust_c = customer(c, "data")
    cid_c = draft(c, cust_c, "E09-DD", starts="2026-10-01").json()["contractId"]
    activate(c, cid_c, "E09-DA")
    original_date = contratos.date
    contratos.date = DataLocal
    try:
        r = c.post(f"/api/v1/contracts/{cid_c}/close", headers=H)
    finally:
        contratos.date = original_date
    show("encerramento sem endsOn (data local simulada 2026-10-18; data UTC 2026-10-19)", r)
