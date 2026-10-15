"""Fachada pública da integração para os módulos de negócio.

As funções participam da transação recebida; somente o caso de uso confirma ou
desfaz a operação. Modelos de outbox, inbox, auditoria e idempotência são internos.
"""
from archcorp.integration.service import IdempotencyStore, LegacyIdService, audit, enqueue

__all__ = ["IdempotencyStore", "LegacyIdService", "audit", "enqueue"]
