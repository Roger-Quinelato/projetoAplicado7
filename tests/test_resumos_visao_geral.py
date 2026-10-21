"""Resumos dos indicadores da Visão geral contados no servidor, sem o limite de 200 das listagens (#73)."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from archcorp.contracts.models import Contract
from archcorp.finance.models import Invoice, Payment
from archcorp.infrastructure.db import SessionLocal
from archcorp.support.models import Ticket
from archcorp.workflow.models import ProcessInstance

ACIMA_DO_LIMITE = 205
CUSTOMER = "c0c0c0c0-c0c0-4c0c-8c0c-c0c0c0c0c0c0"


def _contract(status: str) -> Contract:
    # Cliente próprio por contrato: há unicidade de cliente, serviço e início.
    return Contract(customer_id=str(uuid4()), customer_name="Cliente sintético", customer_email="sintetico@example.com",
                    service_code="RENTAL-FLEX", starts_on=date(2026, 11, 1), amount=Decimal("100.00"), currency="BRL",
                    billing_cycle="MONTHLY", status=status)


def _invoice(status: str, amount: str, currency: str = "BRL", due: date = date(2099, 1, 1)) -> Invoice:
    return Invoice(contract_id=str(uuid4()), customer_id=CUSTOMER, amount=Decimal(amount), currency=currency, due_date=due, status=status)


def _ticket(status: str, due_at: datetime | None) -> Ticket:
    return Ticket(customer_id=CUSTOMER, contract_id=str(uuid4()), service_code="RENTAL-FLEX", category="QUESTION",
                  description="Chamado sintético", status=status, priority="NORMAL", sla_hours=8, due_at=due_at,
                  opened_at=datetime.now(timezone.utc))


def _process(state: str) -> ProcessInstance:
    return ProcessInstance(process_type="ONBOARDING", reference_id=str(uuid4()), customer_id=CUSTOMER, state=state)


def _get(client, headers, path):
    response = client.get(path, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_contratos_acima_de_200_sao_contados(client, admin_headers):
    with SessionLocal() as session:
        session.add_all([_contract("ACTIVE") for _ in range(ACIMA_DO_LIMITE)] + [_contract("DRAFT"), _contract("CLOSED")])
        session.commit()
    assert len(_get(client, admin_headers, "/api/v1/contracts")) == 200
    assert _get(client, admin_headers, "/api/v1/contracts/summary") == {"total": ACIMA_DO_LIMITE + 2, "active": ACIMA_DO_LIMITE}


def test_faturas_a_receber_somam_o_saldo_liquido_por_moeda(client, admin_headers):
    with SessionLocal() as session:
        abertas = [_invoice("OPEN", "10.10") for _ in range(ACIMA_DO_LIMITE)]
        parcial = _invoice("PARTIALLY_PAID", "100.00")
        vencida = _invoice("OPEN", "50.00", due=date(2020, 1, 1))  # vencida na leitura, ainda a receber
        registrada = _invoice("OVERDUE", "30.00", currency="USD")
        session.add_all(abertas + [parcial, vencida, registrada,
                                   _invoice("PAID", "999.00"), _invoice("CANCELLED", "999.00")])
        session.flush()
        session.add_all([Payment(invoice_id=parcial.invoice_id, amount=Decimal("40.25"), currency="BRL", reference=f"R-{uuid4()}"),
                         Payment(invoice_id=parcial.invoice_id, amount=Decimal("9.75"), currency="BRL", reference=f"R-{uuid4()}")])
        session.commit()
    assert len(_get(client, admin_headers, "/api/v1/finance/invoices")) == 200
    summary = _get(client, admin_headers, "/api/v1/finance/invoices/summary")
    assert summary["receivable"] == ACIMA_DO_LIMITE + 3
    # 205 × 10,10 + (100,00 − 50,00) + 50,00 = 2170,50 em BRL; 30,00 em USD.
    assert summary["balances"] == [{"currency": "BRL", "amount": 2170.5}, {"currency": "USD", "amount": 30.0}]


def test_chamados_abertos_e_dentro_do_sla(client, admin_headers):
    futuro = datetime.now(timezone.utc) + timedelta(hours=4)
    passado = datetime.now(timezone.utc) - timedelta(hours=1)
    with SessionLocal() as session:
        session.add_all([_ticket("OPEN", futuro) for _ in range(ACIMA_DO_LIMITE)]
                        + [_ticket("OPEN", passado), _ticket("PENDING_ENTITLEMENT", None), _ticket("RESOLVED", futuro)])
        session.commit()
    assert len(_get(client, admin_headers, "/api/v1/support/tickets")) == 200
    assert _get(client, admin_headers, "/api/v1/support/tickets/summary") == {"open": ACIMA_DO_LIMITE + 1, "withinSla": ACIMA_DO_LIMITE}


def test_processos_em_andamento_excluem_os_finais(client, admin_headers):
    with SessionLocal() as session:
        session.add_all([_process("STARTED") for _ in range(ACIMA_DO_LIMITE)]
                        + [_process("IN_PROGRESS"), _process("COMPLETED"), _process("CANCELLED")])
        session.commit()
    assert len(_get(client, admin_headers, "/api/v1/workflow/processes")) == 200
    assert _get(client, admin_headers, "/api/v1/workflow/processes/summary") == {"total": ACIMA_DO_LIMITE + 3, "running": ACIMA_DO_LIMITE + 1}


def test_resumos_vazios(client, admin_headers):
    assert _get(client, admin_headers, "/api/v1/contracts/summary") == {"total": 0, "active": 0}
    assert _get(client, admin_headers, "/api/v1/finance/invoices/summary") == {"receivable": 0, "balances": []}
    assert _get(client, admin_headers, "/api/v1/support/tickets/summary") == {"open": 0, "withinSla": 0}
    assert _get(client, admin_headers, "/api/v1/workflow/processes/summary") == {"total": 0, "running": 0}


@pytest.mark.parametrize(("path", "permitido", "proibido"), [
    ("/api/v1/contracts/summary", "demo-finance", "demo-operations"),
    ("/api/v1/finance/invoices/summary", "demo-operations", "demo-support"),
    ("/api/v1/support/tickets/summary", "demo-support", "demo-finance"),
    ("/api/v1/workflow/processes/summary", "demo-contracts", "demo-commercial"),
])
def test_resumos_seguem_os_papeis_da_listagem(client, path, permitido, proibido):
    assert client.get(path, headers={"Authorization": f"Bearer {permitido}"}).status_code == 200
    forbidden = client.get(path, headers={"Authorization": f"Bearer {proibido}"})
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "FORBIDDEN"
