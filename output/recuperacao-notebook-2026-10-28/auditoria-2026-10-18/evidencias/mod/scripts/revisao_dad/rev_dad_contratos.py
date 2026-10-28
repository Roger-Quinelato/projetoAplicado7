"""Revisão cruzada da F-MOD sobre o DAD-07 e o DAD-08: exemplos do OpenAPI e Money do AsyncAPI.

Só leitura de docs/api/openapi.yaml e docs/events/asyncapi.yaml; sem banco.
Uso (cwd=<iso-mod>):  python rev_dad_contratos.py
Dependências já instaladas no venv-auditoria: pyyaml, jsonschema, referencing.
"""
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

RAIZ = Path.cwd()
OPENAPI = yaml.safe_load((RAIZ / "docs/api/openapi.yaml").read_text(encoding="utf-8"))
ASYNCAPI = yaml.safe_load((RAIZ / "docs/events/asyncapi.yaml").read_text(encoding="utf-8"))
URI = "urn:openapi"


def reescreve_refs(obj):
    if isinstance(obj, dict):
        return {k: (URI + v if k == "$ref" and isinstance(v, str) and v.startswith("#/") else reescreve_refs(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [reescreve_refs(x) for x in obj]
    return obj


registro = Registry().with_resource(URI, Resource(contents=OPENAPI, specification=DRAFT202012))
exemplos, invalidos = 0, []
for caminho, operacoes in OPENAPI["paths"].items():
    for metodo, operacao in operacoes.items():
        if not isinstance(operacao, dict):
            continue
        pares = []
        corpo = operacao.get("requestBody", {}).get("content", {}).get("application/json")
        if corpo:
            pares.append(("requisição", corpo))
        for status, resposta in operacao.get("responses", {}).items():
            conteudo = resposta.get("content", {}).get("application/json")
            if conteudo:
                pares.append((f"resposta {status}", conteudo))
        for rotulo, midia in pares:
            if "schema" not in midia:
                continue
            esquema = reescreve_refs(midia["schema"])
            valores = []
            if "example" in midia:
                valores.append(("example", midia["example"]))
            for nome, ex in (midia.get("examples") or {}).items():
                if isinstance(ex, dict) and "value" in ex:
                    valores.append((nome, ex["value"]))
            for nome, valor in valores:
                exemplos += 1
                erros = list(Draft202012Validator(esquema, registry=registro, format_checker=FormatChecker()).iter_errors(valor))
                if erros:
                    invalidos.append(f"{metodo.upper()} {caminho} [{rotulo}] {nome}: {erros[0].message[:110]}")
print(f"RESULTADO | OpenAPI: exemplos avaliados | {exemplos}", flush=True)
print(f"RESULTADO | OpenAPI: exemplos inválidos | {len(invalidos)}", flush=True)
for linha in invalidos:
    print("  - " + linha, flush=True)

# DAD-08: Money.amount do AsyncAPI
money = ASYNCAPI["components"]["schemas"].get("Money")
print(f"RESULTADO | AsyncAPI Money.amount | {money['properties']['amount'] if money else 'não encontrado'}", flush=True)
registro_async = Registry().with_resource("urn:async", Resource(contents=ASYNCAPI, specification=DRAFT202012))
validador = Draft202012Validator({"$ref": "urn:async#/components/schemas/Money"}, registry=registro_async, format_checker=FormatChecker())
for valor in (2500.0, 100.1, 19.99, 0.07, 1234567.89):
    erros = [e.message for e in validador.iter_errors({"amount": valor, "currency": "BRL"})]
    print(f"RESULTADO | Money amount={valor} | {'aceito' if not erros else 'rejeitado: ' + erros[0][:70]}", flush=True)
print("FIM | rev_dad_contratos", flush=True)
sys.exit(0)
