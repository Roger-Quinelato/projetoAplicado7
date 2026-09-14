import ast
from pathlib import Path

import yaml

from archcorp.main import app


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
    assert paths["/api/v1/contracts/drafts"]["post"]["responses"]["201"]["content"]["application/json"]["examples"]
    assert paths["/api/v1/support/tickets"]["post"]["responses"]["201"]["content"]["application/json"]["examples"]


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


def test_asyncapi_define_envelope_e_tres_eventos():
    schema = yaml.safe_load(Path("docs/events/asyncapi.yaml").read_text(encoding="utf-8"))
    assert schema["asyncapi"] == "3.0.0"
    assert set(schema["channels"]) == {"contractActivated", "ticketOpened", "customerUpdated"}
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
    assert all(message["examples"] for message in schema["components"]["messages"].values())
