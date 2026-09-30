"""Regenera docs/api/openapi.yaml a partir de app.openapi().

Uso: PYTHONPATH=src python tools/export_openapi.py [--check]
Com --check, falha se o arquivo salvo divergir da aplicação.
"""
import sys
from pathlib import Path

import yaml

from archcorp.main import app

TARGET = Path(__file__).resolve().parents[1] / "docs" / "api" / "openapi.yaml"


def render() -> str:
    return yaml.safe_dump(app.openapi(), allow_unicode=True, sort_keys=False)


def main() -> int:
    content = render()
    if "--check" in sys.argv:
        if yaml.safe_load(TARGET.read_text(encoding="utf-8")) != yaml.safe_load(content):
            print(f"{TARGET} desatualizado. Execute tools/export_openapi.py.", file=sys.stderr)
            return 1
        return 0
    TARGET.write_text(content, encoding="utf-8")
    print(f"OpenAPI exportado para {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
