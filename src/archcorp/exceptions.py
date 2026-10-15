"""Exceções de negócio independentes de HTTP, banco ou framework.

Os casos de uso levantam estas exceções; `archcorp.errors` as converte no
contrato problem+json da API.
"""


class DomainError(Exception):
    """Erro de negócio convertido em problem+json pelo handler global."""

    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, detail: str, *, code: str | None = None):
        """Guarda a mensagem legível e, se informado, substitui o código padrão."""
        super().__init__(detail)
        self.detail = detail
        if code:
            self.code = code


class NotFoundError(DomainError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(DomainError):
    status_code = 409
    code = "CONFLICT"


class IdempotencyConflictError(ConflictError):
    code = "IDEMPOTENCY_CONFLICT"


class InvalidStateError(ConflictError):
    code = "INVALID_STATE"


class BusinessRuleError(DomainError):
    status_code = 422
    code = "BUSINESS_RULE_VIOLATION"
