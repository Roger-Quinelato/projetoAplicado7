"""E-01 (AUD-10 = Q-02) e concorrência de comandos: ativar x ativar, ativar x cancelar, pagamentos e resolução.

Execução registrada: SQLite descartável em <ISO>\\tmp\\e01.db (python e01_concorrencia.py).
PostgreSQL (NÃO executado localmente): ADB_URL=postgresql+psycopg://USUARIO:SENHA@127.0.0.1:5432/BANCO_TESTE
(banco descartável; o roteiro apaga as tabelas). A intercalação é forçada por barreiras colocadas em instância
(sem alterar o código da cópia) entre a leitura do estado e a escrita.
"""
import os
import threading

from dad_common import CID, H, customer, draft, activate, dispatch, reset_db, setup

setup("e01.db")
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from archcorp.contracts.models import Contract, Reservation  # noqa: E402
from archcorp.contracts.service import ReservationService  # noqa: E402
from archcorp.finance.models import Invoice, Payment  # noqa: E402
from archcorp.infrastructure.db import SessionLocal  # noqa: E402
from archcorp.integration.models import OutboxEvent  # noqa: E402
from archcorp.main import app, contracts, finance, tickets  # noqa: E402

reservations = ReservationService(contracts)


def count_events(event_type: str, key: str, value: str) -> int:
    with SessionLocal() as s:
        return s.scalar(select(func.count()).select_from(OutboxEvent).where(
            OutboxEvent.event_type == event_type, OutboxEvent.payload[key].as_string() == value)) or 0


def run_parallel(fns, start_together: bool):
    bar = threading.Barrier(len(fns), timeout=30)
    out = [None] * len(fns)

    def worker(i, fn):
        try:
            if start_together:
                bar.wait()
            out[i] = ("ok", fn())
        except Exception as exc:  # registra a exceção do comando
            out[i] = ("erro", type(exc).__name__, str(exc)[:100])

    threads = [threading.Thread(target=worker, args=(i, fn)) for i, fn in enumerate(fns)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(120)
    return out


def wrap_after(obj, name, bar):
    """Depois da leitura original, espera a outra thread: a escrita só começa com as duas leituras feitas."""
    original = getattr(obj, name)

    def inner(*args, **kwargs):
        result = original(*args, **kwargs)
        bar.wait(timeout=30)
        return result

    setattr(obj, name, inner)
    return lambda: delattr(obj, name)


def scenario_activation_race(c):
    cid = draft(c, customer(c, "a"), "E01-DRAFT-A").json()["contractId"]
    bar = threading.Barrier(2, timeout=30)
    undo = wrap_after(contracts, "eligible_customer", bar)

    def act(key):
        def fn():
            with SessionLocal() as s:
                resp, replay = contracts.activate(s, cid, key, CID)
                return {"eventId": resp["eventId"][:8], "replay": replay}
        return fn

    try:
        res = run_parallel([act("E01-K1"), act("E01-K2")], start_together=False)
    finally:
        undo()
    with SessionLocal() as s:
        status = s.get(Contract, cid).status
    print("A ativação x ativação (chaves diferentes):", res,
          "| ContractActivated.v1 =", count_events("ContractActivated.v1", "contractId", cid),
          "| status =", status)


def scenario_activation_vs_cancel(c):
    cust = customer(c, "b")
    rid = c.post("/api/v1/contracts/reservations", headers={**H, "Idempotency-Key": "E01-RSV-B"}, json={
        "customerId": cust["customerId"], "vehicleGroup": "SUV", "protectionCode": "BASICA",
        "serviceCode": "RENTAL-FLEX", "startsOn": "2027-05-01", "endsOn": "2027-05-05",
        "amount": 300, "currency": "BRL", "billingCycle": "ONCE", "slaHours": 8}).json()["reservationId"]
    cid = c.post(f"/api/v1/contracts/reservations/{rid}/draft", headers={**H, "Idempotency-Key": "E01-RDRAFT-B"}
                 ).json()["contract"]["contractId"]
    barreira = threading.Barrier(2, timeout=30)
    desfazer = [wrap_after(contracts, "eligible_customer", barreira), wrap_after(reservations, "require", barreira)]

    def ativar():
        with SessionLocal() as s:
            resp, _ = contracts.activate(s, cid, "E01-ACT-B", CID)
            return resp["status"]

    def cancelar():
        with SessionLocal() as s:
            return reservations.cancel(s, rid, CID)["status"]

    try:
        resultado = run_parallel([ativar, cancelar], start_together=False)
    finally:
        for f in desfazer:
            f()
    with SessionLocal() as s:
        estado = (s.get(Contract, cid).status, s.get(Reservation, rid).status)
    print("B ativação x cancelamento:", resultado, "| estado final (contrato, reserva) =", estado,
          "| ContractActivated.v1 =", count_events("ContractActivated.v1", "contractId", cid))


def scenario_payments(c):
    cid = draft(c, customer(c, "c"), "E01-DRAFT-C", amount=100, starts="2027-06-01").json()["contractId"]
    activate(c, cid, "E01-ACT-C")
    dispatch(c)
    inv = c.get("/api/v1/finance/invoices", headers=H, params={"contractId": cid}).json()[0]["invoiceId"]
    barreira = threading.Barrier(2, timeout=30)

    def pagar(i):
        def fn():
            with SessionLocal() as s:
                barreira.wait(timeout=30)
                res, _ = finance.record_payment(s, inv, {"amount": 60, "currency": "BRL", "reference": f"E01-REF-{i}"},
                                                f"E01-PAY-{i}", CID)
                return res["invoice"]["status"]
        return fn

    res = run_parallel([pagar(1), pagar(2)], start_together=False)
    with SessionLocal() as s:
        total = s.scalar(select(func.sum(Payment.amount)).where(Payment.invoice_id == inv))
        status = s.get(Invoice, inv).status
    print("C pagamentos simultâneos 60 + 60 sobre fatura de 100:", res,
          "| soma gravada =", total, "| status =", status)


def scenario_resolution(c):
    cust = customer(c, "d")
    cid = draft(c, cust, "E01-DRAFT-D", starts="2027-07-01").json()["contractId"]
    activate(c, cid, "E01-ACT-D")
    tid = c.post("/api/v1/support/tickets", headers={**H, "Idempotency-Key": "E01-TKT-D"}, json={
        "customerId": cust["customerId"], "contractId": cid, "serviceCode": "RENTAL-FLEX",
        "category": "OUTAGE", "description": "Concorrência sintética"}).json()["ticketId"]

    def resolver():
        with SessionLocal() as s:
            resp, _ = tickets.resolve(s, tid, CID, "support", None)
            return resp["status"]

    res = run_parallel([resolver, resolver], start_together=True)
    print("D resolução simultânea do mesmo chamado:", res,
          "| TicketResolved.v1 =", count_events("TicketResolved.v1", "ticketId", tid))


if os.environ.get("ADB_URL"):
    reset_db()
with TestClient(app, raise_server_exceptions=False) as client:
    scenario_activation_race(client)
    scenario_activation_vs_cancel(client)
    scenario_payments(client)
    scenario_resolution(client)
