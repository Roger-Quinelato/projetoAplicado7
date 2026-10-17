"""ADR-006: adaptador de leitura do CRM com prazo, retentativa limitada, atraso exponencial e jitter."""
import pytest

from archcorp.contracts.adapters import ResilientCustomerReader
from archcorp.crm.public import CustomerData, CustomerReaderUnavailableError

CUSTOMER = CustomerData("c-1", "Cliente Sintético", "c1@example.com", eligible=True, consent_service=True)


class ScriptedReader:
    """Devolve ou levanta, em ordem, os itens do roteiro."""

    def __init__(self, *script):
        self.script, self.calls = list(script), 0

    def get(self, session, customer_id):
        self.calls += 1
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class FakeClock:
    def __init__(self):
        self.now, self.sleeps = 0.0, []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def reader(inner, clock, **overrides):
    options = {"timeout_seconds": 10, "max_attempts": 4, "base_delay_seconds": 0.1, "max_delay_seconds": 1.0, "jitter": lambda: 1.0}
    return ResilientCustomerReader(inner, sleep=clock.sleep, clock=clock, **(options | overrides))


def test_sucesso_na_primeira_tentativa_nao_espera():
    clock = FakeClock()
    assert reader(ScriptedReader(CUSTOMER), clock).get(None, "c-1") == CUSTOMER
    assert clock.sleeps == []


def test_cliente_inexistente_nao_e_falha():
    assert reader(ScriptedReader(None), FakeClock()).get(None, "x") is None


def test_erros_transitorios_sao_repetidos_com_atraso_exponencial():
    clock = FakeClock()
    inner = ScriptedReader(TimeoutError(), ConnectionError(), TimeoutError(), CUSTOMER)
    assert reader(inner, clock).get(None, "c-1") == CUSTOMER
    assert inner.calls == 4
    assert clock.sleeps == pytest.approx([0.1, 0.2, 0.4])


def test_atraso_respeita_teto_e_jitter_reduz_ate_a_metade():
    adapter = reader(ScriptedReader(), FakeClock(), base_delay_seconds=0.5, jitter=lambda: 0.0)
    assert [adapter.delay(n) for n in (1, 2, 3, 4)] == pytest.approx([0.25, 0.5, 0.5, 0.5])


def test_tentativas_esgotadas_levantam_indisponibilidade():
    clock = FakeClock()
    inner = ScriptedReader(*[TimeoutError()] * 4)
    with pytest.raises(CustomerReaderUnavailableError):
        reader(inner, clock).get(None, "c-1")
    assert inner.calls == 4
    assert len(clock.sleeps) == 3


def test_prazo_total_interrompe_antes_de_esperar_alem_do_limite():
    clock = FakeClock()
    inner = ScriptedReader(*[ConnectionError()] * 4)
    with pytest.raises(CustomerReaderUnavailableError, match="prazo"):
        reader(inner, clock, timeout_seconds=0.25).get(None, "c-1")
    assert inner.calls == 2
    assert sum(clock.sleeps) < 0.25


def test_erro_nao_transitorio_sobe_sem_retentativa():
    inner = ScriptedReader(ValueError("dado inválido"), CUSTOMER)
    with pytest.raises(ValueError):
        reader(inner, FakeClock()).get(None, "c-1")
    assert inner.calls == 1


def test_configuracao_invalida_e_rejeitada():
    with pytest.raises(ValueError):
        reader(ScriptedReader(), FakeClock(), max_attempts=0)
