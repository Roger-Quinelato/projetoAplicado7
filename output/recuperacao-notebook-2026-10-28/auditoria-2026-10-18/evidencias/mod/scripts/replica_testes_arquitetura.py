"""Réplica da lógica dos testes de fronteira de tests/test_contracts_and_architecture.py (linhas 90-134).

A lógica de cada função é a do teste; a única diferença é a raiz, passada por argumento
(no teste, `Path("src/archcorp")`). Uso:
    python replica_testes_arquitetura.py <raiz_archcorp>
Imprime, por teste, as violações que ele apontaria (lista vazia = passa).
"""
import ast
import sys
from pathlib import Path


def test_modulos_de_negocio_nao_importam_models_de_outro_contexto(root: Path) -> list[str]:
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
    return violations


def test_composicao_da_aplicacao_nao_le_modelos_dos_contextos(root: Path) -> list[str]:
    contexts = {"crm", "contracts", "finance", "support", "workflow", "integration"}
    tree = ast.parse((root / "main.py").read_text(encoding="utf-8"))
    return [
        f"main.py:{node.lineno}:{node.module}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
        and node.module.startswith("archcorp.") and node.module.endswith(".models")
        and node.module.split(".")[1] in contexts
    ]


def test_negocios_usam_apenas_fachada_publica_da_integracao(root: Path) -> list[str]:
    violations = []
    for context in ("crm", "contracts", "finance", "support", "workflow"):
        for path in (root / context).rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("archcorp.integration."):
                    if node.module != "archcorp.integration.public":
                        violations.append(f"{path}:{node.lineno}:{node.module}")
    return violations


def test_dominios_nao_dependem_de_infraestrutura_ou_http(root: Path) -> list[str]:
    violations = []
    for path in root.glob("*/domain.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in {"sqlalchemy", "fastapi", "pydantic"}:
                    violations.append(f"{path}:{node.lineno}:{node.module}")
                if any(part in node.module for part in (".models", ".routes", ".service", ".infrastructure")):
                    violations.append(f"{path}:{node.lineno}:{node.module}")
    return violations


if __name__ == "__main__":
    root = Path(sys.argv[1]).resolve()
    print(f"raiz: {root}")
    for test in (
        test_modulos_de_negocio_nao_importam_models_de_outro_contexto,
        test_composicao_da_aplicacao_nao_le_modelos_dos_contextos,
        test_negocios_usam_apenas_fachada_publica_da_integracao,
        test_dominios_nao_dependem_de_infraestrutura_ou_http,
    ):
        found = test(root)
        print(f"{test.__name__}: {'PASSA' if not found else 'FALHA'} ({len(found)} violação(ões))")
        for item in found:
            print(f"   - {item}")
