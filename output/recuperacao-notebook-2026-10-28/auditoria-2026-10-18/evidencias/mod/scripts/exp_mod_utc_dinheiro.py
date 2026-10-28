"""Comparação de regras duplicadas (F-MOD, item 8): dinheiro e UTC, por leitura direta das funções.

Uso (PYTHONPATH=<ISO>\\src, cwd=<ISO>): python exp_mod_utc_dinheiro.py
Não abre banco: importa as funções com DATABASE_URL em memória.
"""
import os
from datetime import datetime
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.pop("RABBITMQ_URL", None)

from archcorp.contracts.service import money as money_contracts  # noqa: E402
from archcorp.finance.domain import as_utc as finance_as_utc, money as money_finance  # noqa: E402
from archcorp.finance.service import iso_utc as finance_iso_utc  # noqa: E402
from archcorp.support.domain import as_utc as support_as_utc, iso_utc as support_iso_utc  # noqa: E402
from archcorp.workflow.service import _parse_utc as workflow_parse_utc  # noqa: E402


def tentativa(rotulo, funcao):
    try:
        return f"{rotulo} -> {funcao()}"
    except Exception as exc:  # noqa: BLE001 - o objetivo é registrar o comportamento
        return f"{rotulo} -> {type(exc).__name__}: {exc}"


print("DINHEIRO (mesmo valor, duas regras)")
for valor in ("0.125", "0.135", "19.995"):
    print(f"  entrada {valor}: contracts.money={money_contracts(Decimal(valor))} | finance.money={money_finance(Decimal(valor))}")
print("  (contracts usa quantize sem rounding explícito -> ROUND_HALF_EVEN; finance usa ROUND_HALF_UP)")

naive = datetime(2026, 10, 20, 12, 0, 0)
print("UTC (datetime sem fuso, como o SQLite devolve)")
print("  " + tentativa("finance.domain.as_utc(naive)", lambda: finance_as_utc(naive).isoformat()))
print("  " + tentativa("support.domain.as_utc(naive)", lambda: support_as_utc(naive).isoformat()))
print("  " + tentativa("finance.service.iso_utc(naive)", lambda: finance_iso_utc(naive)))
print("  " + tentativa("support.domain.iso_utc(naive)", lambda: support_iso_utc(naive)))
print("  " + tentativa("workflow.service._parse_utc('2026-10-20T12:00:00')", lambda: workflow_parse_utc("2026-10-20T12:00:00").isoformat()))
