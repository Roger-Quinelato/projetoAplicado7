"""F-CFG, item 10 (S-01, S-02) e fatos de agentes: verificações git somente leitura.

Uso (PowerShell, com PY = venv-auditoria):
    PY -I verificar_s01_s02.py <WT> <LOGS>

Cada consulta é um comando git simples executado com `git -C <WT>`. Não altera refs nem o índice.
"""
import subprocess
import sys
from pathlib import Path

WT = Path(sys.argv[1]).resolve()
LOGS = Path(sys.argv[2]).resolve()
linhas = []


def git(*args: str) -> tuple:
    proc = subprocess.run(["git", "-C", str(WT), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def p(texto: str = "") -> None:
    linhas.append(texto)


p("## S-01: merges de PR do pacote de agentes em relacao a origin/main")
for pr, sha in [(45, "4a557da"), (46, "6ad9733"), (47, "893e98f"), (48, "c79cfa1"), (49, "45694c7")]:
    codigo, _, _ = git("merge-base", "--is-ancestor", sha, "origin/main")
    p(f"PR #{pr} ({sha}) ancestral de origin/main: {'sim' if codigo == 0 else 'nao'} (exit={codigo})")
p("")
codigo, saida, _ = git("ls-tree", "-r", "--name-only", "origin/main", "--", ".agents", "tools/perfil_skills.py", "docs/agentes", ".claude/skills")
p("origin/main, caminhos do pacote: " + str(saida.splitlines()))
codigo, saida, _ = git("ls-tree", "-r", "--name-only", "origin/feat/skills-revisor", "--", ".agents", "tools/perfil_skills.py", "docs/agentes", ".claude/skills")
arquivos = saida.splitlines()
p(f"origin/feat/skills-revisor (45694c7), caminhos do pacote: {len(arquivos)} arquivos; "
  f"archcorp-* em .agents: {sum(1 for a in arquivos if a.startswith('.agents/skills/archcorp-') and a.endswith('SKILL.md'))}; "
  f"archcorp-* em .claude/skills: {sum(1 for a in arquivos if a.startswith('.claude/skills/archcorp-') and a.endswith('SKILL.md'))}; "
  f"tools/perfil_skills.py: {'tools/perfil_skills.py' in arquivos}; "
  f"docs/agentes/IMPLEMENTADOR.md: {'docs/agentes/IMPLEMENTADOR.md' in arquivos}; "
  f"docs/agentes/REVISOR.md: {'docs/agentes/REVISOR.md' in arquivos}")
codigo, saida, _ = git("show", "origin/feat/perfil-mcp:.github/workflows/verify.yml")
p("origin/feat/perfil-mcp, verify.yml com validacao do pacote: " + str("perfil_skills.py --check" in saida))
codigo, saida, _ = git("show", "origin/main:.github/workflows/verify.yml")
p("origin/main, verify.yml com validacao do pacote: " + str("perfil_skills.py" in saida))
p("")

p("## S-02: .claude/worktrees/ e .claude/settings.local.json frente ao .gitignore do repositorio")
codigo, saida, _ = git("check-ignore", "-v", "--no-index", ".claude/worktrees/x/y.txt")
p(f"check-ignore .claude/worktrees/x/y.txt: exit={codigo} (1 = nao ignorado)")
codigo, saida, _ = git("check-ignore", "-v", "--no-index", ".claude/settings.local.json")
p(f"check-ignore .claude/settings.local.json: exit={codigo}; regra={saida or '(nenhuma)'}")
p("")

p("## S-03: arquivos PDF versionados (fonte nº 1 citada em AGENTS.md:39)")
codigo, saida, _ = git("ls-files", "*.pdf")
p("pdf versionados: " + str(saida.splitlines()))
p("")

p("## Commit direto em main sem PR (eaad233) e protecao")
codigo, saida, _ = git("log", "-1", "--format=%H %P %ad %s", "--date=short", "eaad233")
p("eaad233: " + saida)

(LOGS / "s01_s02_verificacoes.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
print("\n".join(linhas))
