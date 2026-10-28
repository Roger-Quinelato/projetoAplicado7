"""F-CFG, item 12 e AUD-50: detalhes da governança de refs, somente leitura (git -C WT ...).

Uso (PowerShell, com PY = venv-auditoria):
    PY -I governanca_detalhes.py <WT> <LOGS>

Não cria, move ou remove refs; não faz fetch (usa o estado já baixado) e não altera o índice.
Registra: branches locais sem upstream e sem contenção em remota; divergência local x remoto;
commit de main sem PR; existência do SHA 3fdb533 e da ref execucao-tarefas-pendentes; arquivos de
sincronização versionados; ocorrências de domínios de hospedagem no código (fora de output/).
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


p("## Ref de AUD-50 (execucao-tarefas-pendentes / 3fdb533)")
codigo, saida, _ = git("ls-remote", "--heads", "origin", "execucao-tarefas-pendentes")
p(f"ls-remote origin execucao-tarefas-pendentes: {'ausente' if not saida else saida}")
codigo, saida, _ = git("cat-file", "-t", "3fdb533")
p(f"cat-file -t 3fdb533: codigo={codigo} saida={saida or '(vazio)'}")
codigo, saida, _ = git("reflog", "--all")
p(f"3fdb533 no reflog de todas as refs: {'sim' if '3fdb533' in saida else 'nao'}")
codigo, saida, _ = git("for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes")
p(f"ref com nome contendo 'pendentes' (local ou remota): {[r for r in saida.splitlines() if 'pendentes' in r]}")
p("")

p("## Branches locais sem upstream e sem contenção em nenhuma remota")
codigo, saida, _ = git("for-each-ref", "--format=%(refname:short)|%(upstream:short)|%(objectname:short)|%(committerdate:short)", "refs/heads")
for linha in saida.splitlines():
    ref, upstream, sha, data = linha.split("|")
    contem = git("branch", "-r", "--contains", sha)[1]
    sem_remota = not contem.strip()
    codigo, a_frente, _ = git("rev-list", "--count", f"origin/main..{ref}")
    if sem_remota or not upstream:
        p(f"  {ref}: sha={sha} data={data} upstream={upstream or '-'} commits_fora_da_main={a_frente} contido_em_remota={'nao' if sem_remota else 'sim'}")
p("")

p("## Divergencia entre local e upstream (ahead/behind), branches com upstream")
codigo, saida, _ = git("for-each-ref", "--format=%(refname:short)|%(upstream:short)", "refs/heads")
for linha in saida.splitlines():
    ref, upstream = linha.split("|")
    if not upstream:
        continue
    codigo, lr, _ = git("rev-list", "--left-right", "--count", f"{upstream}...{ref}")
    atras, adiante = (lr.split() + ["0", "0"])[:2]
    if atras != "0" or adiante != "0":
        p(f"  {ref} vs {upstream}: so_no_remoto={atras} so_no_local={adiante}")
p("")

p("## Commit de main sem PR (eaad233) e merges sem PR")
codigo, saida, _ = git("log", "-1", "--format=%H|%P|%ad|%s", "--date=short", "eaad233")
p(f"eaad233: {saida}")
codigo, saida, _ = git("log", "--first-parent", "--format=%h|%P|%s", "origin/main", "-n", "12")
for linha in saida.splitlines():
    sha, pais, assunto = linha.split("|", 2)
    if "#" not in assunto:
        p(f"  sem numero de PR no assunto: {sha} parents={len(pais.split())} {assunto}")
p("")

p("## Arquivos de sincronizacao versionados (docs/*_SYNC.json, JIRA_*.json)")
codigo, saida, _ = git("ls-files", "docs")
p("  versionados: " + str([l for l in saida.splitlines() if "SYNC" in l or "JIRA_" in l]))
p("")

p("## Domínios de hospedagem em codigo e configuracao (fora de output/ e docs/)")
for padrao in ["onrender.com", "supabase.co"]:
    codigo, saida, _ = git("grep", "-l", "-i", padrao, "--", ":!output", ":!docs")
    p(f"  {padrao} em codigo/configuracao: arquivos={saida.splitlines() if saida else []}")
codigo, saida, _ = git("grep", "-l", "-i", "onrender.com", "--", "docs")
p(f"  onrender.com em docs/ (apenas contagem; texto nao avaliado): arquivos={len(saida.splitlines()) if saida else 0}")
p("")

p("## Worktrees")
codigo, saida, _ = git("worktree", "list", "--porcelain")
p(saida)

(LOGS / "governanca_detalhes.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
print(f"linhas={len(linhas)}")
