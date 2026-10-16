"""Perfil de carga de skills (tools/perfil_skills.py, docs/agentes/pacote-skills.json).

Usa um repositório e uma "home" falsos em tmp_path: nenhum teste lê a
biblioteca pessoal real nem grava fora do diretório temporário.
"""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("perfil_skills", "tools/perfil_skills.py")
perfil = importlib.util.module_from_spec(spec)
spec.loader.exec_module(perfil)

MANIFEST = {
    "versao": 1,
    "projeto": "archcorp",
    "pastas_do_projeto": [".claude/skills", ".agents/skills"],
    "prefixo_obrigatorio": "archcorp-",
    "skills_legadas_do_projeto": ["caveman"],
    "limite_linhas_skill": 20,
    "pacote": [{"nome": "archcorp-revisao", "pasta": ".agents/skills"}],
    "skills_pessoais_permitidas": ["research"],
    "plugins_mantidos": ["document-skills@anthropic-agent-skills"],
    "desligar_sincronizacao_claude_ai": True,
    "desligar_conectores_claude_ai": False,
}


def write_skill(folder: Path, name: str, description: str = "Quando usar.", lines: int = 0) -> None:
    (folder / name).mkdir(parents=True)
    body = "\n".join(f"linha {i}" for i in range(lines))
    (folder / name / "SKILL.md").write_text(f"---\nname: {name}\ndescription: >\n  {description}\n---\n{body}\n", encoding="utf-8")


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "docs/agentes").mkdir(parents=True)
    (root / "docs/agentes/pacote-skills.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
    write_skill(root / ".agents/skills", "archcorp-revisao")
    write_skill(root / ".claude/skills", "caveman")
    return root


@pytest.fixture
def home(tmp_path):
    home = tmp_path / "home"
    for name in ("caveman", "research", "dengue-df-lag-features", "implement"):
        write_skill(home / ".claude/skills", name)
        write_skill(home / ".agents/skills", name)
    (home / ".claude/plugins").mkdir(parents=True)
    (home / ".claude/plugins/installed_plugins.json").write_text(
        json.dumps({"version": 2, "plugins": {"document-skills@anthropic-agent-skills": [], "twilio@market": []}}), encoding="utf-8")
    return home


def run(repo, home, *args):
    return perfil.main(["--root", str(repo), "--home", str(home), *args])


def test_pacote_real_do_repositorio_e_valido():
    root = Path(".").resolve()
    assert perfil.check(root, perfil.load_manifest(root)) == []


def test_perfil_esconde_so_o_que_nao_e_do_projeto_nem_permitido(repo, home):
    profile, warnings = perfil.build_profile(repo, home, MANIFEST)
    assert profile["skillOverrides"] == {"dengue-df-lag-features": "off", "implement": "off"}
    assert profile["enabledPlugins"] == {"document-skills@anthropic-agent-skills": True, "twilio@market": False}
    assert (profile["syncClaudeAiPlugins"], profile["syncClaudeAiSkills"]) == (False, False)
    assert "disableClaudeAiConnectors" not in profile
    assert warnings == ["caveman: a skill pessoal de mesmo nome tem precedência sobre a do projeto"]


def test_gravacao_preserva_ajustes_manuais_e_remove_o_que_o_perfil_anterior_criou(repo, home):
    local = repo / ".claude/settings.local.json"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(json.dumps({"permissions": {"allow": ["Bash(ls)"]}, "skillOverrides": {"manual": "name-only"}}), encoding="utf-8")
    assert run(repo, home) == 0
    first = json.loads(local.read_text(encoding="utf-8"))
    assert first["permissions"] == {"allow": ["Bash(ls)"]}
    assert first["skillOverrides"] == {"manual": "name-only", "dengue-df-lag-features": "off", "implement": "off"}

    manifest = {**MANIFEST, "skills_pessoais_permitidas": ["research", "implement"]}
    (repo / "docs/agentes/pacote-skills.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert run(repo, home) == 0
    second = json.loads(local.read_text(encoding="utf-8"))
    assert second["skillOverrides"] == {"manual": "name-only", "dengue-df-lag-features": "off"}  # implement voltou a aparecer
    assert json.loads((repo / ".claude/perfil-archcorp.json").read_text(encoding="utf-8"))["skillOverrides"] == {"dengue-df-lag-features": "off"}


def test_conectores_so_sao_desligados_quando_o_manifesto_pede(repo, home):
    profile, _ = perfil.build_profile(repo, home, {**MANIFEST, "desligar_conectores_claude_ai": True})
    assert profile["disableClaudeAiConnectors"] is True
    merged = perfil.merge_local({"disableClaudeAiConnectors": True}, {"disableClaudeAiConnectors": True}, perfil.build_profile(repo, home, MANIFEST)[0])
    assert "disableClaudeAiConnectors" not in merged  # desligar a opção no manifesto desfaz o que o perfil gravou


@pytest.mark.parametrize("break_repo, message", [
    (lambda root: write_skill(root / ".agents/skills", "solta"), "solta: skill nova sem o prefixo"),
    (lambda root: write_skill(root / ".agents/skills", "archcorp-extra"), "archcorp-extra: ausente de 'pacote'"),
    (lambda root: write_skill(root / ".claude/skills", "archcorp-revisao"), "archcorp-revisao: existe em mais de uma pasta"),
    (lambda root: (root / ".agents/skills/archcorp-revisao/SKILL.md").write_text("---\nname: outro\ndescription: x\n---\n", encoding="utf-8"),
     "difere do nome da pasta"),
    (lambda root: (root / ".agents/skills/archcorp-revisao/SKILL.md").write_text("---\nname: archcorp-revisao\n---\n", encoding="utf-8"),
     "description ausente"),
    (lambda root: ((root / ".agents/skills/archcorp-revisao/SKILL.md").unlink(), (root / ".agents/skills/archcorp-revisao").rmdir()),
     "declarada no pacote, mas"),
])
def test_check_reprova_pacote_invalido(repo, home, capsys, break_repo, message):
    break_repo(repo)
    assert run(repo, home, "--check") == 1
    assert message in capsys.readouterr().err
    assert not (repo / ".claude/settings.local.json").exists()  # nada é gravado com o pacote inválido


def test_skill_externa_do_projeto_exige_registro_no_lock(repo):
    write_skill(repo / ".agents/skills", "humanizer", lines=30)  # sem prefixo e acima do limite
    manifest = {**MANIFEST, "skills_externas_do_projeto": ["humanizer"]}
    assert perfil.check(repo, manifest) == ["humanizer: skill externa sem registro em skills-lock.json (instale com npx skills add)"]
    (repo / "skills-lock.json").write_text(json.dumps({"version": 1, "skills": {"humanizer": {"source": "blader/humanizer"}}}), encoding="utf-8")
    assert perfil.check(repo, manifest) == []


def test_check_reprova_skill_acima_do_limite_de_linhas(repo, home, capsys):
    (repo / ".agents/skills/archcorp-revisao").rename(repo / "tmp-old")
    write_skill(repo / ".agents/skills", "archcorp-revisao", lines=25)
    assert run(repo, home, "--check") == 1
    assert "excede 20 linhas" in capsys.readouterr().err


def test_bloco_do_codex_desliga_so_as_skills_fora_da_lista(repo, home, capsys):
    assert run(repo, home, "--codex") == 0
    block = capsys.readouterr().out
    assert block.count("[[skills.config]]") == 2
    assert "dengue-df-lag-features" in block and "implement" in block
    assert "research" not in block and "caveman" not in block
    assert "enabled = false" in block and "path = '" in block  # literal string TOML: barras do Windows sem escape


def test_codex_esconde_sub_skills_aninhadas_e_skills_de_sistema(repo, home):
    write_skill(home / ".agents/skills/dengue-df-lag-features", "sub-skill")  # aninhada em skill escondida
    write_skill(home / ".agents/skills/research", "grounded-citations")  # aninhada em skill permitida
    write_skill(home / ".codex/skills", "colab-slide")
    write_skill(home / ".codex/skills/.system", "imagegen")
    hidden = {path.parent.name for path in perfil.codex_hidden(repo, home, MANIFEST)}
    assert {"sub-skill", "colab-slide", "imagegen", "implement", "dengue-df-lag-features"} <= hidden
    assert not hidden & {"research", "grounded-citations", "caveman"}


def test_valor_inline_do_codex_para_a_opcao_c(repo, home, capsys):
    assert run(repo, home, "--codex-inline") == 0
    value = capsys.readouterr().out.strip()
    assert value.startswith("skills.config=[{path='") and value.endswith("enabled=false}]")
    assert value.count("enabled=false") == 2 and "research" not in value
