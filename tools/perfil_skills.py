"""Perfil de carga de skills do projeto (docs/agentes/pacote-skills.json).

Faz Claude e Codex enxergarem, neste repositório, só o pacote do projeto em vez
de toda a biblioteca pessoal. A biblioteca pessoal não é alterada: as skills
fora da lista permitida são escondidas por configuração local.

Uso:
    python tools/perfil_skills.py --check    # valida o pacote (CI; não lê a máquina pessoal)
    python tools/perfil_skills.py --dry-run  # mostra o perfil sem gravar
    python tools/perfil_skills.py            # grava .claude/settings.local.json e .claude/perfil-archcorp.json
    python tools/perfil_skills.py --codex    # imprime o bloco [[skills.config]] do Codex
    python tools/perfil_skills.py --codex-inline  # valor para `codex -c` (só aquela invocação)

`.claude/perfil-archcorp.json` serve para `claude --settings` em worktrees e
execuções automáticas e registra o que este script escreveu: ao regenerar, só
essas entradas saem do settings.local.json; ajustes manuais são preservados.
"""
import argparse
import json
import sys
from pathlib import Path

MANIFEST = Path("docs/agentes/pacote-skills.json")
LOCAL_SETTINGS = Path(".claude/settings.local.json")
PROFILE = Path(".claude/perfil-archcorp.json")
MANAGED_SCALARS = ("syncClaudeAiPlugins", "syncClaudeAiSkills", "disableClaudeAiConnectors")


def load_manifest(root: Path) -> dict:
    """Lê o manifesto versionado do pacote."""
    return json.loads((root / MANIFEST).read_text(encoding="utf-8"))


def frontmatter(text: str) -> dict:
    """Extrai as chaves de primeiro nível do frontmatter YAML, inclusive blocos `>` e `|`."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields, key = {}, None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line[:1] not in (" ", "\t") and ":" in line:
            key, value = line.split(":", 1)
            key, value = key.strip(), value.strip()
            fields[key] = "" if value in (">", "|", ">-", "|-") else value.strip("\"'")
        elif key and line.strip():
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def skill_dirs(folder: Path) -> dict[str, Path]:
    """Mapeia nome da pasta → pasta para cada subpasta com SKILL.md."""
    if not folder.is_dir():
        return {}
    return {p.name: p for p in sorted(folder.iterdir()) if (p / "SKILL.md").is_file()}


def project_skills(root: Path, manifest: dict) -> dict[str, list[Path]]:
    """Skills versionadas no projeto, por nome (uma lista para detectar duplicatas)."""
    found: dict[str, list[Path]] = {}
    for folder in manifest["pastas_do_projeto"]:
        for name, path in skill_dirs(root / folder).items():
            found.setdefault(name, []).append(path)
    return found


def check(root: Path, manifest: dict) -> list[str]:
    """Valida o pacote do projeto; devolve a lista de erros (vazia quando válido)."""
    errors = []
    prefix, legacy = manifest["prefixo_obrigatorio"], set(manifest["skills_legadas_do_projeto"])
    found = project_skills(root, manifest)
    declared = {entry["nome"]: entry for entry in manifest["pacote"]}
    for name, paths in found.items():
        if len(paths) > 1:
            errors.append(f"{name}: existe em mais de uma pasta do projeto ({', '.join(str(p.relative_to(root)) for p in paths)})")
        path = paths[0]
        text = (path / "SKILL.md").read_text(encoding="utf-8")
        fields = frontmatter(text)
        if fields.get("name") != name:
            errors.append(f"{name}: o campo name do frontmatter ({fields.get('name')!r}) difere do nome da pasta")
        if not fields.get("description"):
            errors.append(f"{name}: description ausente no frontmatter")
        if name in legacy:
            continue
        if not name.startswith(prefix):
            errors.append(f"{name}: skill nova sem o prefixo {prefix!r}")
        if name not in declared:
            errors.append(f"{name}: ausente de 'pacote' em {MANIFEST.as_posix()}")
        if len(text.splitlines()) > manifest["limite_linhas_skill"]:
            errors.append(f"{name}: SKILL.md excede {manifest['limite_linhas_skill']} linhas; mover detalhes para references/")
    for name, entry in declared.items():
        expected = root / entry["pasta"] / name / "SKILL.md"
        if not expected.is_file():
            errors.append(f"{name}: declarada no pacote, mas {expected.relative_to(root).as_posix()} não existe")
    return errors


def installed_plugins(home: Path) -> list[str]:
    """Identificadores dos plugins instalados localmente no Claude Code."""
    path = home / ".claude/plugins/installed_plugins.json"
    if not path.is_file():
        return []
    return sorted(json.loads(path.read_text(encoding="utf-8")).get("plugins", {}))


def allowed_names(root: Path, manifest: dict) -> set[str]:
    """Nomes que nunca são escondidos: skills do projeto e pessoais permitidas."""
    return set(project_skills(root, manifest)) | set(manifest["skills_pessoais_permitidas"])


def build_profile(root: Path, home: Path, manifest: dict) -> tuple[dict, list[str]]:
    """Calcula as chaves geridas do perfil e os avisos de colisão de nome."""
    allowed = allowed_names(root, manifest)
    personal = skill_dirs(home / ".claude/skills")
    profile: dict = {"skillOverrides": {name: "off" for name in personal if name not in allowed}}
    kept = set(manifest["plugins_mantidos"])
    plugins = sorted(set(installed_plugins(home)) | kept)
    profile["enabledPlugins"] = {plugin: plugin in kept for plugin in plugins}
    if manifest["desligar_sincronizacao_claude_ai"]:
        profile["syncClaudeAiPlugins"] = False
        profile["syncClaudeAiSkills"] = False
    if manifest["desligar_conectores_claude_ai"]:
        profile["disableClaudeAiConnectors"] = True
    shadowed = sorted(set(personal) & set(project_skills(root, manifest)))
    warnings = [f"{name}: a skill pessoal de mesmo nome tem precedência sobre a do projeto" for name in shadowed]
    return profile, warnings


def merge_local(existing: dict, previous: dict, profile: dict) -> dict:
    """Aplica o perfil ao settings.local.json sem apagar ajustes manuais.

    Entradas que o perfil anterior criou e o novo não recria são removidas;
    as demais chaves e entradas do usuário são preservadas.
    """
    merged = dict(existing)
    for key in ("skillOverrides", "enabledPlugins"):
        own = {k: v for k, v in existing.get(key, {}).items() if k not in previous.get(key, {})}
        own.update(profile[key])
        if own:
            merged[key] = own
        else:
            merged.pop(key, None)
    for key in MANAGED_SCALARS:
        if key in profile:
            merged[key] = profile[key]
        elif key in previous:
            merged.pop(key, None)
    return merged


def codex_hidden(root: Path, home: Path, manifest: dict) -> list[Path]:
    """SKILL.md das skills pessoais do Codex fora da lista permitida."""
    allowed = allowed_names(root, manifest)
    return [path / "SKILL.md" for name, path in skill_dirs(home / ".agents/skills").items() if name not in allowed]


def codex_block(root: Path, home: Path, manifest: dict) -> str:
    """Bloco TOML `[[skills.config]]` (forma de config.toml e de agente .codex/agents/*.toml)."""
    return "\n".join(f"[[skills.config]]\npath = '{path}'\nenabled = false\n" for path in codex_hidden(root, home, manifest))


def codex_inline(root: Path, home: Path, manifest: dict) -> str:
    """Valor para `codex -c` (verificado no codex-cli 0.163.0): desliga as skills só naquela invocação."""
    items = ", ".join(f"{{path='{path}', enabled=false}}" for path in codex_hidden(root, home, manifest))
    return f"skills.config=[{items}]"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="só valida o pacote do projeto")
    parser.add_argument("--dry-run", action="store_true", help="mostra o perfil sem gravar")
    parser.add_argument("--codex", action="store_true", help="imprime o bloco [[skills.config]] do Codex")
    parser.add_argument("--codex-inline", action="store_true", help="imprime o valor para `codex -c` (por invocação)")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--home", type=Path, default=Path.home())
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")  # console do Windows usa cp1252 por padrão

    manifest = load_manifest(args.root)
    errors = check(args.root, manifest)
    for error in errors:
        print(f"ERRO {error}", file=sys.stderr)
    if errors:
        return 1
    if args.check:
        print(f"Pacote válido: {len(project_skills(args.root, manifest))} skills do projeto.")
        return 0
    if args.codex:
        print(codex_block(args.root, args.home, manifest))
        return 0
    if args.codex_inline:
        print(codex_inline(args.root, args.home, manifest))
        return 0

    profile, warnings = build_profile(args.root, args.home, manifest)
    for warning in warnings:
        print(f"AVISO {warning}", file=sys.stderr)
    hidden = len(profile["skillOverrides"])
    if args.dry_run:
        print(json.dumps(profile, indent=2, ensure_ascii=False))
        return 0
    local_path, profile_path = args.root / LOCAL_SETTINGS, args.root / PROFILE
    merged = merge_local(read_json(local_path), read_json(profile_path), profile)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    profile_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Perfil gravado: {hidden} skills pessoais escondidas; plugins mantidos: {', '.join(manifest['plugins_mantidos']) or 'nenhum'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
