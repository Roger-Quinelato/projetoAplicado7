"""Metadados de respostas da API v1, sem estado da aplicação."""
from archcorp.contracts.service import CRM_UNAVAILABLE_DETAIL
from archcorp.errors import problem_content, problem_example
from archcorp.api_examples import (EXAMPLE_CONTRACT_ACTIVATED_RESPONSE, EXAMPLE_CONTRACT_DRAFT_RESPONSE, EXAMPLE_CONTRACT_EVENT_ID, EXAMPLE_CONTRACT_ID, EXAMPLE_CORRELATION_ID, EXAMPLE_PENDING_TICKET_RESPONSE, EXAMPLE_TICKET_RESPONSE)


CORRELATION_REQUEST_PARAMETER = {
    "name": "X-Correlation-ID",
    "in": "header",
    "required": False,
    "description": "UUID de correlação. A API gera um UUID quando o cabeçalho é omitido.",
    "schema": {"type": "string", "format": "uuid"},
    "example": EXAMPLE_CORRELATION_ID,
}


CORRELATION_RESPONSE_HEADER = {
    "description": "UUID usado para correlacionar a requisição, os logs e os eventos.",
    "schema": {"type": "string", "format": "uuid"},
    "example": EXAMPLE_CORRELATION_ID,
}


IDEMPOTENCY_RESPONSE_HEADERS = {
    "X-Correlation-ID": CORRELATION_RESPONSE_HEADER,
    "Idempotency-Replayed": {
        "description": "Retorna true quando a API reutiliza a resposta armazenada.",
        "schema": {"type": "string", "enum": ["true", "false"]},
        "example": "false",
    },
}


def validation_problem_response(description: str, instance: str, field: str, rule_summary: str, rule_detail: str) -> dict:
    invalid = [{"type": "uuid_parsing", "loc": ["body", field], "msg": "Entrada inválida"}]
    return {
        "description": description,
        "content": problem_content(examples={
            "businessRule": {"summary": rule_summary, "value": problem_example(422, rule_detail, instance, "BUSINESS_RULE_VIOLATION")},
            "validation": {"summary": "Corpo da requisição inválido", "value": {**problem_example(422, invalid, instance), "errors": invalid}},
        }),
    }


COMMON_API_ERRORS = {
    400: {
        "description": "Cabeçalho de correlação inválido.",
        "content": problem_content(problem_example(400, "X-Correlation-ID deve ser UUID", "/api/v1/contracts/drafts")),
    },
    401: {
        "description": "Token ausente ou inválido.",
        "content": problem_content(problem_example(401, "Token ausente ou inválido", "/api/v1/contracts/drafts")),
    },
    403: {
        "description": "Papel sem permissão para a operação.",
        "content": problem_content(problem_example(403, "Papel sem permissão para esta operação", "/api/v1/contracts/drafts")),
    },
}


CONTRACT_DRAFT_RESPONSES = {
    **COMMON_API_ERRORS,
    201: {
        "description": "Rascunho criado ou resposta idempotente recuperada.",
        "headers": IDEMPOTENCY_RESPONSE_HEADERS,
        "content": {
            "application/json": {
                "examples": {
                    "created": {
                        "summary": "Rascunho criado",
                        "value": EXAMPLE_CONTRACT_DRAFT_RESPONSE,
                    },
                    "replayed": {
                        "summary": "Resposta recuperada com Idempotency-Replayed true",
                        "value": EXAMPLE_CONTRACT_DRAFT_RESPONSE,
                    },
                }
            }
        },
    },
    409: {
        "description": "Idempotency-Key reutilizada com outro conteúdo ou contrato já existente.",
        "content": problem_content(problem_example(409, "Idempotency-Key já utilizada com outro contrato", "/api/v1/contracts/drafts", "IDEMPOTENCY_CONFLICT")),
    },
    422: validation_problem_response(
        "Entrada inválida ou cliente inexistente, inelegível ou sem consentimento.",
        "/api/v1/contracts/drafts", "customerId",
        "Cliente não pode originar contrato", "Cliente inexistente ou inelegível",
    ),
    503: {
        "description": "CRM indisponível após as retentativas; nenhum efeito foi gravado (ADR-006).",
        "content": problem_content(problem_example(503, CRM_UNAVAILABLE_DETAIL, "/api/v1/contracts/drafts")),
    },
}


CONTRACT_ACTIVATION_RESPONSES = {
    **COMMON_API_ERRORS,
    200: {
        "description": "Contrato ativado ou resposta idempotente recuperada.",
        "headers": IDEMPOTENCY_RESPONSE_HEADERS,
        "content": {
            "application/json": {
                "examples": {
                    "activated": {
                        "summary": "Contrato ativado e evento gravado na outbox",
                        "value": EXAMPLE_CONTRACT_ACTIVATED_RESPONSE,
                    },
                    "replayed": {
                        "summary": "Resposta recuperada com Idempotency-Replayed true",
                        "value": EXAMPLE_CONTRACT_ACTIVATED_RESPONSE,
                    },
                }
            }
        },
    },
    404: {
        "description": "Contrato não encontrado.",
        "content": problem_content(problem_example(404, "Contrato não encontrado", "/api/v1/contracts/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/activate")),
    },
    409: {
        "description": "Contrato já encerrado ou estado incompatível para ativação.",
        "content": problem_content(problem_example(409, "Somente contrato em rascunho pode ser ativado", "/api/v1/contracts/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/activate", "INVALID_STATE")),
    },
    503: {
        "description": "CRM indisponível na revalidação do cliente; o contrato continua em rascunho (ADR-006).",
        "content": problem_content(problem_example(503, CRM_UNAVAILABLE_DETAIL, "/api/v1/contracts/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/activate")),
    },
}


ENTITLEMENT_RESPONSES = {
    **COMMON_API_ERRORS,
    200: {
        "description": "Elegibilidade e SLA do contrato.",
        "headers": {"X-Correlation-ID": CORRELATION_RESPONSE_HEADER},
        "content": {
            "application/json": {
                "examples": {
                    "eligible": {
                        "summary": "Contrato elegível",
                        "value": {"eligible": True, "slaHours": 8},
                    },
                    "notEligible": {
                        "summary": "Contrato não elegível",
                        "value": {"eligible": False, "slaHours": None},
                    },
                }
            }
        },
    },
}


TICKET_RESPONSES = {
    **COMMON_API_ERRORS,
    201: {
        "description": "Chamado criado ou resposta idempotente recuperada.",
        "headers": IDEMPOTENCY_RESPONSE_HEADERS,
        "content": {
            "application/json": {
                "examples": {
                    "open": {
                        "summary": "Chamado elegível aberto",
                        "value": EXAMPLE_TICKET_RESPONSE,
                    },
                    "pending": {
                        "summary": "Chamado pendente por indisponibilidade de Contracts",
                        "value": EXAMPLE_PENDING_TICKET_RESPONSE,
                    },
                    "replayed": {
                        "summary": "Resposta recuperada com Idempotency-Replayed true",
                        "value": EXAMPLE_TICKET_RESPONSE,
                    },
                }
            }
        },
    },
    409: {
        "description": "Idempotency-Key reutilizada com outro chamado.",
        "content": problem_content(problem_example(409, "Idempotency-Key já utilizada com outro chamado", "/api/v1/support/tickets", "IDEMPOTENCY_CONFLICT")),
    },
    422: validation_problem_response(
        "Entrada inválida ou contrato, serviço ou cliente sem elegibilidade.",
        "/api/v1/support/tickets", "contractId",
        "Contrato sem elegibilidade", "Contrato, serviço ou cliente sem elegibilidade",
    ),
}


RECONCILIATION_RESPONSES = {
    **COMMON_API_ERRORS,
    200: {
        "description": "Chamado reconciliado, ou resposta original recuperada pela mesma Idempotency-Key.",
        "headers": {
            "X-Correlation-ID": CORRELATION_RESPONSE_HEADER,
            "Idempotency-Replayed": {
                "description": "true quando o chamado já havia sido reconciliado e nenhum efeito novo foi gravado.",
                "schema": {"type": "string", "enum": ["true", "false"]},
                "example": "false",
            },
        },
        "content": {
            "application/json": {
                "examples": {
                    "open": {
                        "summary": "Elegibilidade confirmada",
                        "value": EXAMPLE_TICKET_RESPONSE,
                    },
                    "rejected": {
                        "summary": "Elegibilidade rejeitada",
                        "value": {
                            **EXAMPLE_PENDING_TICKET_RESPONSE,
                            "status": "REJECTED_ENTITLEMENT",
                            "slaStatus": "NOT_APPLICABLE",
                        },
                    },
                }
            }
        },
    },
    404: {
        "description": "Chamado não encontrado.",
        "content": problem_content(problem_example(404, "Chamado não encontrado", "/api/v1/support/tickets/dddddddd-dddd-4ddd-8ddd-dddddddddddd/reconcile")),
    },
    409: {
        "description": "Chamado não está pendente de elegibilidade.",
        "content": problem_content(problem_example(409, "Somente chamado pendente pode ser reconciliado", "/api/v1/support/tickets/dddddddd-dddd-4ddd-8ddd-dddddddddddd/reconcile", "INVALID_STATE")),
    },
    503: {
        "description": "Contracts ainda indisponível; o chamado permanece pendente.",
        "content": problem_content(problem_example(503, "Contracts indisponível; o chamado permanece em PENDING_ENTITLEMENT", "/api/v1/support/tickets/dddddddd-dddd-4ddd-8ddd-dddddddddddd/reconcile")),
    },
}


DISPATCH_RESPONSES = {
    **COMMON_API_ERRORS,
    200: {
        "description": "Resumo do despacho dos eventos pendentes.",
        "headers": {"X-Correlation-ID": CORRELATION_RESPONSE_HEADER},
        "content": {
            "application/json": {"example": {"processed": 1, "failed": 0}}
        },
    },
}


OUTBOX_SUMMARY_RESPONSES = {
    **COMMON_API_ERRORS,
    200: {
        "description": "Quantidade de eventos aguardando despacho e de eventos com falha permanente.",
        "headers": {"X-Correlation-ID": CORRELATION_RESPONSE_HEADER},
        "content": {
            "application/json": {"example": {"pending": 3, "failed": 0}}
        },
    },
}


FAILURE_LIST_RESPONSES = {
    **COMMON_API_ERRORS,
    200: {
        "description": "Eventos que atingiram o limite de tentativas.",
        "headers": {"X-Correlation-ID": CORRELATION_RESPONSE_HEADER},
        "content": {
            "application/json": {
                "example": [
                    {
                        "eventId": EXAMPLE_CONTRACT_EVENT_ID,
                        "eventType": "ContractActivated.v1",
                        "attempts": 3,
                        "reason": "dependência simulada indisponível",
                        "correlationId": EXAMPLE_CORRELATION_ID,
                    }
                ]
            }
        },
    },
}


REPROCESS_RESPONSES = {
    **COMMON_API_ERRORS,
    200: {
        "description": "Evento recolocado em PENDING para novo despacho.",
        "headers": {"X-Correlation-ID": CORRELATION_RESPONSE_HEADER},
        "content": {
            "application/json": {
                "example": {
                    "eventId": EXAMPLE_CONTRACT_EVENT_ID,
                    "status": "PENDING",
                }
            }
        },
    },
    404: {
        "description": "Evento com falha não encontrado.",
        "content": problem_content(problem_example(404, "Falha não encontrada", "/api/v1/integration/failures/cccccccc-cccc-4ccc-8ccc-cccccccccccc/reprocess")),
    },
}


OPERATION_TRACE_RESPONSES = {
    **COMMON_API_ERRORS,
    200: {
        "description": "Auditoria e eventos vinculados ao correlationId.",
        "headers": {"X-Correlation-ID": CORRELATION_RESPONSE_HEADER},
        "content": {
            "application/json": {
                "example": {
                    "correlationId": EXAMPLE_CORRELATION_ID,
                    "audit": [
                        {
                            "occurredAt": "2026-10-01T10:00:00Z",
                            "module": "contracts",
                            "operation": "activate_contract",
                            "result": "success",
                            "entityId": EXAMPLE_CONTRACT_ID,
                            "details": {},
                        }
                    ],
                    "events": [
                        {
                            "eventId": EXAMPLE_CONTRACT_EVENT_ID,
                            "eventType": "ContractActivated.v1",
                            "status": "PUBLISHED",
                            "attempts": 0,
                        }
                    ],
                }
            }
        },
    },
}

