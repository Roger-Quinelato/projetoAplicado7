"""Contrato único de erro da API (RFC 9457, application/problem+json).

O corpo mantém o campo `detail` usado pelos clientes da versão 1 e acrescenta
`code`, `correlationId` e `errors`. Em erros de validação (422), `detail`
continua sendo a lista de erros do FastAPI para não quebrar clientes existentes;
a mesma lista também é exposta em `errors`.
"""
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError

from archcorp.exceptions import DomainError
from archcorp.observability import correlation_id_var, logger
from archcorp.schemas import EXAMPLE_CONTRACT_ID, EXAMPLE_CORRELATION_ID


PROBLEM_MEDIA_TYPE = "application/problem+json"
STATUS_CODES = {
    400: ("BAD_REQUEST", "Requisição inválida"),
    401: ("UNAUTHORIZED", "Não autenticado"),
    403: ("FORBIDDEN", "Acesso negado"),
    404: ("NOT_FOUND", "Recurso não encontrado"),
    409: ("CONFLICT", "Conflito"),
    422: ("VALIDATION_ERROR", "Entrada inválida"),
    500: ("INTERNAL_ERROR", "Erro interno"),
    503: ("SERVICE_UNAVAILABLE", "Dependência indisponível"),
}


class ProblemDetails(BaseModel):
    """Corpo de erro publicado no OpenAPI."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "urn:archcorp:problem:not-found",
                    "title": "Recurso não encontrado",
                    "status": 404,
                    "detail": "Contrato não encontrado",
                    "instance": f"/api/v1/contracts/{EXAMPLE_CONTRACT_ID}",
                    "code": "NOT_FOUND",
                    "correlationId": EXAMPLE_CORRELATION_ID,
                }
            ]
        }
    )

    type: str = Field(description="URI que identifica o tipo do problema.")
    title: str
    status: int
    detail: str | list[dict[str, Any]] = Field(
        description="Mensagem legível. Em 422 mantém a lista de erros da versão 1."
    )
    instance: str = Field(description="Caminho da requisição que originou o erro.")
    code: str = Field(description="Código estável para tratamento pelo cliente.")
    correlationId: str
    errors: list[dict[str, Any]] | None = None


def problem_type(code: str) -> str:
    return "urn:archcorp:problem:" + code.lower().replace("_", "-")


def problem_body(status: int, detail: Any, instance: str, correlation_id: str, code: str | None = None) -> dict[str, Any]:
    default_code, title = STATUS_CODES.get(status, (f"HTTP_{status}", "Erro HTTP"))
    code = code or default_code
    return {
        "type": problem_type(code),
        "title": title,
        "status": status,
        "detail": detail,
        "instance": instance,
        "code": code,
        "correlationId": correlation_id,
    }


def problem_response(
    request: Request,
    status: int,
    detail: Any,
    *,
    code: str | None = None,
    errors: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = problem_body(status, detail, request.url.path, correlation_id_var.get(), code)
    if errors is not None:
        body["errors"] = errors
    return JSONResponse(
        jsonable_encoder(body),
        status_code=status,
        headers=headers,
        media_type=PROBLEM_MEDIA_TYPE,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return problem_response(request, exc.status_code, exc.detail, headers=getattr(exc, "headers", None))


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return problem_response(request, exc.status_code, exc.detail, code=exc.code)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = jsonable_encoder(exc.errors())
    return problem_response(request, 422, errors, errors=errors)


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("Violação de unicidade ou integridade", extra={"operation": request.url.path, "result": "conflict"})
    return problem_response(request, 409, "Conflito com registro existente", code="CONFLICT")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)


def problem_content(example: dict[str, Any] | None = None, examples: dict[str, Any] | None = None) -> dict:
    """Bloco `content` do OpenAPI para respostas de erro."""
    media: dict[str, Any] = {"schema": {"$ref": "#/components/schemas/ProblemDetails"}}
    if examples:
        media["examples"] = examples
    elif example:
        media["example"] = example
    return {PROBLEM_MEDIA_TYPE: media}


def problem_example(status: int, detail: Any, instance: str, code: str | None = None) -> dict[str, Any]:
    return problem_body(status, detail, instance, EXAMPLE_CORRELATION_ID, code)


def install_problem_openapi(app: FastAPI) -> None:
    """Publica `ProblemDetails` e documenta 422 como problem+json em todas as operações."""
    original = app.openapi

    def openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = original()
        schemas = schema.setdefault("components", {}).setdefault("schemas", {})
        schemas["ProblemDetails"] = ProblemDetails.model_json_schema(ref_template="#/components/schemas/{model}")
        for name in ("HTTPValidationError", "ValidationError"):
            schemas.pop(name, None)
        for path, operations in schema.get("paths", {}).items():
            for operation in operations.values():
                document_problem_responses(path, operation)
        app.openapi_schema = schema
        return schema

    app.openapi = openapi


VALIDATION_ERROR_EXAMPLE = {
    "type": "missing",
    "loc": ["body", "name"],
    "msg": "Field required",
    "input": {},
}


CORRELATION_PARAMETER = {
    "name": "X-Correlation-ID",
    "in": "header",
    "required": False,
    "description": "UUID de correlação. A API gera um UUID quando o cabeçalho é omitido.",
    "schema": {"type": "string", "format": "uuid"},
    "example": EXAMPLE_CORRELATION_ID,
}
DEFAULT_PROBLEMS = {
    "401": ("Token ausente ou inválido.", "Token ausente ou inválido"),
    "403": ("Papel sem permissão para a operação.", "Papel sem permissão para esta operação"),
    "404": ("Recurso não encontrado.", "Recurso não encontrado"),
}


def document_problem_responses(path: str, operation: dict) -> None:
    """Completa cada operação com as respostas de erro que ela pode produzir."""
    responses = operation.setdefault("responses", {})
    parameters = operation.setdefault("parameters", [])
    if path.startswith("/api/") and not any(p.get("name") == "X-Correlation-ID" for p in parameters):
        parameters.append(CORRELATION_PARAMETER)
    expected = []
    if operation.get("security"):
        expected += ["401", "403"]
    if any(p.get("in") == "path" for p in parameters):
        expected.append("404")
    for status in expected:
        if status not in responses:
            description, detail = DEFAULT_PROBLEMS[status]
            responses[status] = {"description": description, "content": problem_content(problem_example(int(status), detail, path))}
    for status, response in responses.items():
        if not status.isdigit() or int(status) < 400:
            continue
        content = response.get("content", {})
        if status == "422" and "application/json" in content and PROBLEM_MEDIA_TYPE not in content:
            response["description"] = "Entrada inválida."
            response["content"] = problem_content(problem_example(422, [VALIDATION_ERROR_EXAMPLE], path) | {"errors": [VALIDATION_ERROR_EXAMPLE]})
        elif not content:
            detail = response.get("description", "Erro").rstrip(".")
            response["content"] = problem_content(problem_example(int(status), detail, path))
    operation["responses"] = dict(sorted(responses.items()))
