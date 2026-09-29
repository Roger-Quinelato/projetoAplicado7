import ast
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate as validate_openapi
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from archcorp.infrastructure.db import SessionLocal
from archcorp.integration.models import OutboxEvent
from archcorp.main import app, dispatcher

ASYNCAPI_URI = "urn:archcorp:asyncapi"


def load_asyncapi() -> dict:
    return yaml.safe_load(Path("docs/events/asyncapi.yaml").read_text(encoding="utf-8"))


def asyncapi_validator(document: dict, message: str) -> Draft202012Validator:
    registry = Registry().with_resource(ASYNCAPI_URI, Resource(contents=document, specification=DRAFT202012))
    return Draft202012Validator({"$ref": f"{ASYNCAPI_URI}#/components/messages/{message}/payload"}, registry=registry)


def test_openapi_expoe_fluxos_e_seguranca():
    schema = app.openapi()
    required = {
        "/api/v1/contracts/drafts",
        "/api/v1/contracts/{contract_id}/activate",
        "/api/v1/support/tickets",
        "/api/v1/operations/{correlation_id}",
    }
    assert required.issubset(schema["paths"])
    assert "HTTPBearer" in schema["components"]["securitySchemes"]


def test_openapi_salvo_corresponde_a_aplicacao_e_documenta_exemplos():
    generated = app.openapi()
    saved = yaml.safe_load(Path("docs/api/openapi.yaml").read_text(encoding="utf-8"))
    assert saved == generated

    schemas = generated["components"]["schemas"]
    assert schemas["CustomerCreate"]["examples"]
    assert schemas["ContractDraftCreate"]["examples"]
    assert schemas["TicketCreate"]["examples"]

    paths = generated["paths"]
    contract_response = paths["/api/v1/contracts/drafts"]["post"]["responses"]["201"]["content"]["application/json"]
    ticket_response = paths["/api/v1/support/tickets"]["post"]["responses"]["201"]["content"]["application/json"]
    assert contract_response["examples"]
    assert contract_response["schema"]["$ref"].endswith("/ContractDraftResponse")
    assert ticket_response["examples"]
    assert ticket_response["schema"]["$ref"].endswith("/TicketResponse")

    assert schemas["ContractDraftCreate"]["properties"]["customerId"]["format"] == "uuid"
    assert schemas["TicketCreate"]["properties"]["contractId"]["format"] == "uuid"


def test_api_rejeita_identificadores_globais_que_nao_sao_uuid(client, admin_headers):
    draft = client.post(
        "/api/v1/contracts/drafts",
        headers={**admin_headers, "Idempotency-Key": "invalid-draft-id"},
        json={
            "customerId": "not-a-uuid",
            "serviceCode": "RENTAL-FLEX",
            "startsOn": "2026-10-01",
            "billing": {"amount": 2500, "currency": "BRL", "cycle": "MONTHLY"},
            "slaHours": 8,
        },
    )
    assert draft.status_code == 422
    assert draft.json()["detail"][0]["loc"] == ["body", "customerId"]

    ticket = client.post(
        "/api/v1/support/tickets",
        headers={**admin_headers, "Idempotency-Key": "invalid-ticket-id"},
        json={
            "customerId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "contractId": "not-a-uuid",
            "serviceCode": "RENTAL-FLEX",
            "category": "OUTAGE",
            "description": "Identificador inválido",
        },
    )
    assert ticket.status_code == 422
    assert ticket.json()["detail"][0]["loc"] == ["body", "contractId"]


def test_modulos_de_negocio_nao_importam_models_de_outro_contexto():
    root = Path("src/archcorp")
    contexts = {"crm", "contracts", "finance", "support", "workflow"}
    violations = []
    for context in contexts:
        for file in (root / context).glob("*.py"):
            tree = ast.parse(file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    parts = node.module.split(".")
                    if len(parts) >= 3 and parts[0] == "archcorp" and parts[1] in contexts - {context} and parts[2] == "models":
                        violations.append(f"{file}:{node.lineno}:{node.module}")
    assert violations == []


def test_asyncapi_define_envelope_e_eventos_atuais():
    schema = load_asyncapi()
    assert schema["asyncapi"] == "3.0.0"
    addresses = {channel["address"] for channel in schema["channels"].values()}
    assert addresses == set(dispatcher.handlers)
    required = schema["components"]["schemas"]["EventEnvelope"]["required"]
    assert {
        "eventId",
        "eventType",
        "eventVersion",
        "occurredAt",
        "correlationId",
        "causationId",
        "producer",
        "payload",
    }.issubset(required)

    causation_id = schema["components"]["schemas"]["EventEnvelope"]["properties"]["causationId"]
    assert set(causation_id["type"]) == {"string", "null"}
    assert causation_id["format"] == "uuid"
    for message in schema["components"]["messages"].values():
        assert message["examples"]
        assert all(example.get("summary") for example in message["examples"])
    for channel in schema["channels"].values():
        assert channel["bindings"]["$ref"] == "#/components/channelBindings/archcorpEvents"
    assert schema["components"]["channelBindings"]["archcorpEvents"]["amqp"]["exchange"]["name"] == "archcorp.events"


def test_exemplos_asyncapi_validam_contra_os_schemas():
    document = load_asyncapi()
    for name, message in document["components"]["messages"].items():
        validator = asyncapi_validator(document, name)
        for example in message["examples"]:
            errors = [error.message for error in validator.iter_errors(example["payload"])]
            assert errors == [], f"{name}/{example['name']}: {errors}"


def test_envelopes_publicados_validam_contra_asyncapi(client, admin_headers, integrated_contract):
    customer, contract = integrated_contract
    client.patch(f"/api/v1/crm/customers/{customer['customerId']}", headers=admin_headers, json={"name": "Empresa Contrato"})
    client.post(f"/api/v1/contracts/{contract['contractId']}/activate", headers={**admin_headers, "Idempotency-Key": "envelope-activate"})
    ticket = client.post("/api/v1/support/tickets", headers={**admin_headers, "Idempotency-Key": "envelope-ticket"}, json={
        "customerId": customer["customerId"], "contractId": contract["contractId"], "serviceCode": "RENTAL-FLEX",
        "category": "OUTAGE", "description": "Validação de envelope",
    }).json()
    client.post(f"/api/v1/support/tickets/{ticket['ticketId']}/resolve", headers=admin_headers)
    assert client.post("/api/v1/integration/outbox/dispatch", headers=admin_headers).json()["failed"] == 0

    document = load_asyncapi()
    messages = {message["name"]: key for key, message in document["components"]["messages"].items()}
    with SessionLocal() as session:
        envelopes = [event.envelope() for event in session.query(OutboxEvent)]
    assert {envelope["eventType"] for envelope in envelopes} >= {"CustomerUpdated.v1", "ContractActivated.v1", "TicketOpened.v1", "TicketResolved.v1"}
    for envelope in envelopes:
        assert envelope["occurredAt"].endswith("Z")
        validator = asyncapi_validator(document, messages[envelope["eventType"]])
        errors = [error.message for error in validator.iter_errors(envelope)]
        assert errors == [], f"{envelope['eventType']}: {errors}"


def test_openapi_valido_com_exemplos_e_erros_problem_json():
    schema = app.openapi()
    validate_openapi(schema)
    components = schema["components"]["schemas"]
    assert "ProblemDetails" in components
    missing_examples, untyped_errors = [], []
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            for status, response in operation["responses"].items():
                for media_type, media in response.get("content", {}).items():
                    if status.startswith("2") and media_type == "application/json":
                        ref = media.get("schema", {}).get("$ref") or media.get("schema", {}).get("items", {}).get("$ref")
                        documented = "example" in media or "examples" in media or bool(ref and components[ref.split("/")[-1]].get("examples"))
                        if not documented:
                            missing_examples.append(f"{method.upper()} {path} {status}")
                if int(status) >= 400 and set(response.get("content", {})) != {"application/problem+json"}:
                    untyped_errors.append(f"{method.upper()} {path} {status}")
            if operation.get("security"):
                assert {"401", "403"}.issubset(operation["responses"]), f"{method.upper()} {path}"
    assert missing_examples == []
    assert untyped_errors == []
