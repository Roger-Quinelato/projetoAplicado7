"""Fixtures dos testes do fluxo coordenado.

Ficam fora de tests/ de propósito: não carregam a fixture global que limpa o banco da aplicação
nem dependem de PostgreSQL ou RabbitMQ. Os agentes são o executável falso fake_agente.py.
"""
import importlib.util
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
FAKE = Path(__file__).resolve().parent / "fake_agente.py"


def _carregar_fluxo():
    spec = importlib.util.spec_from_file_location("fluxo_archcorp", RAIZ / "tools/fluxo_archcorp.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


fluxo = _carregar_fluxo()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


@dataclass
class Ambiente:
    repo: Path
    estado: Path
    cenario_arquivo: Path

    def cenario(self, codex=(), claude=()) -> None:
        self.cenario_arquivo.write_text(json.dumps({"codex": list(codex), "claude": list(claude)}), encoding="utf-8")

    def rodar(self, *argv: str) -> int:
        return fluxo.main(["--repo", str(self.repo), *argv])

    def pedido(self, texto: str = "Corrigir a soma em src/app.py\n\nA função soma subtrai.") -> Path:
        caminho = self.estado.parent / "pedido com espaço.md"
        caminho.write_text(texto, encoding="utf-8")
        return caminho

    def execucao(self, ident: str) -> dict:
        return json.loads((self.repo / ".agentes/execucoes" / ident / "estado.json").read_text(encoding="utf-8"))

    def chamadas(self, papel: str | None = None) -> list[dict]:
        log = self.estado / "chamadas.jsonl"
        if not log.exists():
            return []
        itens = [json.loads(linha) for linha in log.read_text(encoding="utf-8").splitlines()]
        return [i for i in itens if papel is None or i["papel"] == papel]


@pytest.fixture
def amb(tmp_path, monkeypatch) -> Ambiente:
    repo = tmp_path / "repo com espaço"
    (repo / "src").mkdir(parents=True)
    (repo / ".gitignore").write_text(".agentes/\n", encoding="utf-8")
    (repo / "AGENTS.md").write_text("# AGENTS.md\n\nRegras de teste.\n", encoding="utf-8")
    (repo / "README.md").write_text("# Repositório de teste\n", encoding="utf-8")
    (repo / "src/app.py").write_text("def soma(a, b):\n    return a - b\n", encoding="utf-8")
    for perfil in (".claude/agents/archcorp-implementer.md", ".codex/agents/archcorp-coordinator-reviewer.toml",
                   "docs/agentes/PROTOCOLO.md"):
        (repo / perfil).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RAIZ / perfil, repo / perfil)
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    git(repo, "config", "user.name", "Teste")
    git(repo, "config", "user.email", "teste@example.invalid")
    sem_excludes = tmp_path / "sem-excludes"
    sem_excludes.write_text("", encoding="utf-8")
    git(repo, "config", "core.excludesFile", str(sem_excludes))  # isola do ignore global da máquina
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    estado = tmp_path / "fake"
    estado.mkdir()
    ambiente = Ambiente(repo, estado, tmp_path / "cenario.json")
    ambiente.cenario()
    monkeypatch.setenv("FAKE_ESTADO", str(estado))
    monkeypatch.setenv("FAKE_CENARIO", str(ambiente.cenario_arquivo))
    monkeypatch.setenv("ARCHCORP_FLUXO_CODEX", json.dumps([sys.executable, str(FAKE), "codex"]))
    monkeypatch.setenv("ARCHCORP_FLUXO_CLAUDE", json.dumps([sys.executable, str(FAKE), "claude"]))
    monkeypatch.setenv("ARCHCORP_FLUXO_TIMEOUT", "60")
    monkeypatch.delenv("ARCHCORP_FLUXO_FALHA_APOS", raising=False)
    return ambiente
