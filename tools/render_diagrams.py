"""Renderiza os diagramas Mermaid da documentação em PNG para o relatório e a apresentação.

Uso: python tools/render_diagrams.py

Requer o mermaid-cli (`npx @mermaid-js/mermaid-cli`). Defina `MMDC` com o caminho do
executável `mmdc` para evitar o npx e `PUPPETEER_CONFIG` com um JSON de configuração do
puppeteer quando o Chromium precisar ser indicado explicitamente.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "arquitetura" / "img"

# Nome do PNG -> (documento de origem, posição do bloco mermaid no documento, começando em 0).
DIAGRAMS = {
    "as_is": ("docs/arquitetura/AS_IS.md", 0),
    "to_be_componentes": ("docs/arquitetura/TO_BE.md", 0),
    "to_be_implantacao": ("docs/arquitetura/TO_BE.md", 1),
    "f1_cliente_contrato": ("docs/arquitetura/FLUXOS_INTEGRACAO.md", 0),
    "f2_ativacao_cobranca": ("docs/arquitetura/FLUXOS_INTEGRACAO.md", 1),
    "f3_chamado_sla": ("docs/arquitetura/FLUXOS_INTEGRACAO.md", 2),
}

BLOCK = re.compile(r"```mermaid\n(.*?)```", re.S)


def mmdc_command():
    """Retorna o comando do mermaid-cli, priorizando a variável MMDC."""
    if os.environ.get("MMDC"):
        return [os.environ["MMDC"]]
    npx = shutil.which("npx")
    if not npx:
        sys.exit("mermaid-cli indisponível: defina MMDC ou instale Node.js com npx.")
    return [npx, "-y", "@mermaid-js/mermaid-cli@11.4.2"]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = mmdc_command()
    config = os.environ.get("PUPPETEER_CONFIG")
    with tempfile.TemporaryDirectory() as tmp:
        for name, (doc, index) in DIAGRAMS.items():
            blocks = BLOCK.findall((ROOT / doc).read_text(encoding="utf-8"))
            if index >= len(blocks):
                sys.exit(f"{doc} não tem o bloco mermaid {index}.")
            source = Path(tmp) / f"{name}.mmd"
            source.write_text(blocks[index], encoding="utf-8")
            target = OUT_DIR / f"{name}.png"
            cmd = base + ["-i", str(source), "-o", str(target), "-b", "white", "-s", "2", "-w", "1400"]
            if config:
                cmd += ["-p", config]
            subprocess.run(cmd, check=True)
            print(target.relative_to(ROOT))


if __name__ == "__main__":
    main()
