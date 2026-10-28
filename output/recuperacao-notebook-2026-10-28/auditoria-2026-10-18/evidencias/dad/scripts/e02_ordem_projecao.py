"""E-02 (Q-03 = AUD-04): CustomerUpdated.v1 antigo reprocessado depois da versão mais nova (SQLite executado).

Controle: sem falha, a ordem normal (v1 e depois v2) deixa a projeção na v2.
Cenário: a v1 falha três vezes (falha transitória injetada no consumidor de produção), a v2 é aplicada e a v1 é
reprocessada pelo endpoint de reprocessamento. A fonte oficial é o CRM (GET /crm/customers).
"""
from dad_common import H, customer, draft, dispatch, setup

setup("e02.db")
from fastapi.testclient import TestClient  # noqa: E402

from archcorp.config import settings  # noqa: E402
from archcorp.contracts.models import Contract  # noqa: E402
from archcorp.infrastructure.db import SessionLocal  # noqa: E402
from archcorp.main import app, dispatcher  # noqa: E402

PRODUCAO = dispatcher.handlers["CustomerUpdated.v1"]
PROJECAO = PRODUCAO[0][1]


def projection(contract_id):
    with SessionLocal() as s:
        return s.get(Contract, contract_id).customer_name


def rename(c, cust, name):
    return c.patch(f"/api/v1/crm/customers/{cust['customerId']}", headers=H, json={"name": name})


with TestClient(app, raise_server_exceptions=False) as c:
    ctrl = customer(c, "ctrl")
    cid_ctrl = draft(c, ctrl, "E02-CTRL").json()["contractId"]
    rename(c, ctrl, "Controle Versao 1")
    dispatch(c)
    rename(c, ctrl, "Controle Versao 2")
    dispatch(c)
    print("controle sem falha: projeção =", projection(cid_ctrl))

    cust = customer(c, "ord")
    cid = draft(c, cust, "E02-DRAFT").json()["contractId"]
    rename(c, cust, "Nome Versao 1")
    estado = {"falha": True}

    def consumidor_com_falha(session, envelope):
        if envelope["payload"]["name"] == "Nome Versao 1" and estado["falha"]:
            raise RuntimeError("falha transitória simulada")
        PROJECAO(session, envelope)

    dispatcher.handlers["CustomerUpdated.v1"] = [("contracts-customer-projection", consumidor_com_falha)]
    for i in range(settings.retry_limit):
        print(f"despacho {i + 1} (v1 falhando):", dispatch(c))
    rename(c, cust, "Nome Versao 2")
    print("despacho com v2:", dispatch(c), "| projeção =", projection(cid))
    estado["falha"] = False
    falhas = c.get("/api/v1/integration/failures", headers=H).json()
    print("falhas listadas:", [(f["eventType"], f["attempts"], f["reason"][:40]) for f in falhas])
    r = c.post(f"/api/v1/integration/failures/{falhas[0]['eventId']}/reprocess", headers=H)
    print("reprocessamento da v1:", r.status_code, r.json())
    print("despacho após reprocessamento:", dispatch(c), "| projeção =", projection(cid))
    crm = c.get(f"/api/v1/crm/customers/{cust['customerId']}", headers=H).json()
    print("fonte oficial (CRM):", crm["name"])
    dispatcher.handlers["CustomerUpdated.v1"] = PRODUCAO
