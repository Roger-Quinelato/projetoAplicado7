"""Baseline separado do OpenAPI regenerado: mudanças incompatíveis exigem revisão."""
import copy
import json
from pathlib import Path

from archcorp.main import app

BASELINE = json.loads(Path("tests/fixtures/api_v1_baseline.json").read_text())
METADATA = {"title", "description", "example", "examples", "default", "deprecated", "summary"}


def contract(value):
    if isinstance(value, dict):
        return {key: ({field: contract(schema) for field, schema in item.items()} if key == "properties" else contract(item))
                for key, item in value.items() if key not in METADATA}
    if isinstance(value, list):
        return [contract(item) for item in value]
    return value


def compatibility_errors(current):
    """Guarda proporcional: operações/status/mídia, parâmetros e propriedades v1.

    Não substitui caracterizações de comportamento e efeitos de F1–F3. Aceita
    campos/respostas novos; as duas alterações de schema ADR-003 são exatas.
    """
    errors = []
    schemas = current["components"]["schemas"]
    for name, previous in BASELINE["schemas"].items():
        now = schemas.get(name)
        if now is None:
            errors.append(f"schema removido: {name}")
            continue
        for field, schema in previous.get("properties", {}).items():
            expected = BASELINE["approved_ADR003"].get(f"{name}.{field}", schema)
            if contract(now.get("properties", {}).get(field)) != expected:
                errors.append(f"propriedade incompatível: {name}.{field}")
        if name.endswith("Response") and set(previous.get("required", [])) - set(now.get("required", [])):
            errors.append(f"campo de resposta deixou de ser garantido: {name}")
    for path, methods in BASELINE["paths"].items():
        for method, previous in methods.items():
            label = f"{method.upper()} {path}"
            now = current.get("paths", {}).get(path, {}).get(method)
            if now is None:
                errors.append(f"operação removida: {label}")
                continue
            # Exceções de segurança aprovadas e justificadas no baseline (approved_security).
            if now.get("security") != BASELINE.get("approved_security", {}).get(label, previous.get("security")):
                errors.append(f"segurança incompatível: {label}")
            old_params = {(p["in"], p["name"]): p for p in previous.get("parameters", [])}
            params = {(p["in"], p["name"]): p for p in now.get("parameters", [])}
            for key, parameter in old_params.items():
                if key not in params or contract(params[key]) != parameter:
                    errors.append(f"parâmetro incompatível: {label} {key}")
            if any(p.get("required") for key, p in params.items() if key not in old_params):
                errors.append(f"parâmetro obrigatório novo: {label}")
            if contract(now.get("requestBody")) != previous.get("requestBody"):
                errors.append(f"corpo incompatível: {label}")
            for status, response in previous["responses"].items():
                actual = now.get("responses", {}).get(status)
                if actual is None:
                    errors.append(f"status removido: {label} {status}")
                    continue
                for media, content in response.get("content", {}).items():
                    if contract(actual.get("content", {}).get(media, {}).get("schema")) != content.get("schema"):
                        errors.append(f"resposta incompatível: {label} {status} {media}")
    # Nenhuma entrada existente passa a exigir um campo novo.
    for name in (name for name in BASELINE["schemas"] if name.endswith(("Input", "Create", "Update", "Change"))):
        if set(schemas[name].get("required", [])) - set(BASELINE["schemas"][name].get("required", [])):
            errors.append(f"campo obrigatório novo: {name}")
    return errors


def test_contrato_v1_compativel_com_baseline_e_excecoes_explicitas():
    assert compatibility_errors(app.openapi()) == []


def test_guarda_detecta_restricao_nova_rota_removida_e_cabecalho_obrigatorio():
    altered = copy.deepcopy(app.openapi())
    altered["components"]["schemas"]["TicketCreate"]["properties"]["description"]["maxLength"] = 10
    del altered["paths"]["/api/v1/support/tickets"]
    altered["paths"]["/api/v1/support/tickets/{ticket_id}/resolve"]["post"]["parameters"].append({
        "name": "New-Required", "in": "header", "required": True, "schema": {"type": "string"},
    })
    errors = compatibility_errors(altered)
    assert any("TicketCreate.description" in error for error in errors)
    assert any("operação removida" in error for error in errors)
    assert any("parâmetro obrigatório novo" in error for error in errors)


def test_guarda_detecta_seguranca_alterada_fora_das_excecoes_aprovadas():
    altered = copy.deepcopy(app.openapi())
    altered["paths"]["/health/live"]["get"]["security"] = [{"HTTPBearer": []}]
    altered["paths"]["/metrics"]["get"].pop("security", None)
    errors = compatibility_errors(altered)
    assert "segurança incompatível: GET /health/live" in errors
    assert "segurança incompatível: GET /metrics" in errors
