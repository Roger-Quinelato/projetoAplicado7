"""Adaptadores de saída de Contracts para portas de outros contextos."""

import random
import time

from sqlalchemy.orm import Session

from archcorp.crm.public import CustomerData, CustomerReader, CustomerReaderUnavailableError
from archcorp.observability import logger

TRANSIENT_ERRORS = (TimeoutError, ConnectionError)


class ResilientCustomerReader:
    """Envolve a porta do CRM com prazo total, retentativa limitada e tradução da indisponibilidade (ADR-006).

    Só `TimeoutError` e `ConnectionError` são transitórios; qualquer outro erro sobe sem nova tentativa.
    O prazo limita tentativas e esperas somadas. No processo único a leitura não pode ser interrompida;
    o corte de cada chamada cabe ao cliente HTTP do conector quando o CRM sair do processo.
    """

    def __init__(self, inner: CustomerReader, *, timeout_seconds: float, max_attempts: int,
                 base_delay_seconds: float, max_delay_seconds: float = 1.0,
                 sleep=time.sleep, clock=time.monotonic, jitter=random.random):
        """Recebe a porta real e os limites; relógio, espera e jitter são injetáveis nos testes."""
        if max_attempts < 1:
            raise ValueError("max_attempts deve ser pelo menos 1")
        self.inner = inner
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.sleep = sleep
        self.clock = clock
        self.jitter = jitter

    def delay(self, attempt: int) -> float:
        """Atraso exponencial limitado, com jitter entre 50% e 100% do valor."""
        ceiling = min(self.max_delay_seconds, self.base_delay_seconds * 2 ** (attempt - 1))
        return ceiling * (0.5 + self.jitter() / 2)

    def get(self, session: Session, customer_id: str) -> CustomerData | None:
        """Lê o cliente; repete só erros transitórios e levanta CustomerReaderUnavailableError ao esgotar."""
        deadline = self.clock() + self.timeout_seconds
        reason = "prazo esgotado"
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self.inner.get(session, customer_id)
            except TRANSIENT_ERRORS as exc:
                reason = type(exc).__name__
                logger.warning(f"CRM indisponível na leitura do cliente (tentativa {attempt} de {self.max_attempts}, {reason})",
                               extra={"operation": "crm_customer_read", "result": "retry"})
            if attempt == self.max_attempts:
                break
            wait = self.delay(attempt)
            if self.clock() + wait >= deadline:
                reason = f"prazo de {self.timeout_seconds:g}s esgotado"
                break
            self.sleep(wait)
        raise CustomerReaderUnavailableError(f"CRM indisponível ({reason})")
