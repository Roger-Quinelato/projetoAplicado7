"""F-CFG, item 13 (e AUD-42, AUD-49, AUD-50): leitura do GitHub somente com chamadas GET.

Uso (PowerShell, com PY = venv-auditoria):
    PY -I github_leitura.py <LOGS>

Só executa `gh api <caminho>` (método GET implícito) e `gh run list` / `gh pr list`. Nenhuma
chamada altera issues, PRs, branches, proteções, Jira, Trello, Notion ou Drive. Erros de
permissão (403) e ausência de recurso (404) são registrados como "não verificável" ou
"não configurado", com a mensagem da API truncada. Tokens não são lidos nem impressos.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

LOGS = Path(sys.argv[1]).resolve()
REPO = "Roger-Quinelato/projetoAplicado7"
SHA_CI = "44b83254b43bfcc043766d69b9fb6b8970330cbf"
RUN_CI = "39063148796"
JOB_APP = "117485116908"
JOB_RABBIT = "117485117016"
JOB_PG = "117485116770"

CHAMADAS = [
    ("repo", f"repos/{REPO}", ["--jq", "{default_branch, visibility, archived, allow_forking, delete_branch_on_merge, security_and_analysis}"]),
    ("branch_main", f"repos/{REPO}/branches/main", ["--jq", "{name, protected}"]),
    ("protecao_main", f"repos/{REPO}/branches/main/protection", []),
    ("rulesets", f"repos/{REPO}/rulesets", []),
    ("alertas_vulnerabilidade_habilitados", f"repos/{REPO}/vulnerability-alerts", []),
    ("dependabot_alertas_abertos", f"repos/{REPO}/dependabot/alerts?state=open&per_page=5", ["--jq", "length"]),
    ("secret_scanning_alertas_abertos", f"repos/{REPO}/secret-scanning/alerts?state=open&per_page=5", ["--jq", "length"]),
    ("code_scanning_alertas_abertos", f"repos/{REPO}/code-scanning/alerts?state=open&per_page=5", ["--jq", "length"]),
    ("actions_permissoes", f"repos/{REPO}/actions/permissions", []),
    ("actions_permissoes_workflow", f"repos/{REPO}/actions/permissions/workflow", []),
    ("deployments", f"repos/{REPO}/deployments?per_page=5", ["--jq", "length"]),
    ("issue_23_t20", f"repos/{REPO}/issues/23", ["--jq", "{state, comments, labels: [.labels[].name]}"]),
    ("run_ci_39063148796", f"repos/{REPO}/actions/runs/{RUN_CI}", ["--jq", "{conclusion, head_sha, event, created_at, path}"]),
    ("jobs_ci_39063148796", f"repos/{REPO}/actions/runs/{RUN_CI}/jobs", ["--jq", ".jobs[] | {id, name, conclusion}"]),
    ("check_runs_sha_auditado", f"repos/{REPO}/commits/{SHA_CI}/check-runs", ["--jq", ".check_runs[] | {name, conclusion}"]),
    ("status_sha_auditado", f"repos/{REPO}/commits/{SHA_CI}/status", ["--jq", "{state, total_count}"]),
]


def gh(args: list) -> tuple:
    proc = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def main() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    linhas = [f"coleta UTC: {agora}", f"repositorio: {REPO}", ""]
    resumo = {}
    for rotulo, caminho, extra in CHAMADAS:
        codigo, saida, erro = gh(["api", caminho, *extra])
        if codigo == 0:
            resumo[rotulo] = "ok"
            linhas.append(f"### {rotulo} (GET {caminho})")
            linhas.append(saida if saida else "(resposta vazia: 204 ou sem conteudo)")
        else:
            trecho = (erro or saida).replace("\n", " ")[:300]
            resumo[rotulo] = "erro"
            linhas.append(f"### {rotulo} (GET {caminho}) -> ERRO")
            linhas.append(trecho)
        linhas.append("")
    # Execuções do workflow verify.yml, para ver os gatilhos reais (branch e evento).
    codigo, saida, erro = gh(["run", "list", "--repo", REPO, "--workflow", "verify.yml", "--limit", "30",
                              "--json", "databaseId,headBranch,event,conclusion,createdAt,headSha"])
    linhas.append("### execucoes_verify_yml (gh run list)")
    if codigo == 0:
        execucoes = json.loads(saida or "[]")
        por_ramo = {}
        for item in execucoes:
            chave = (item["headBranch"], item["event"])
            por_ramo[chave] = por_ramo.get(chave, 0) + 1
        for (ramo, evento), total in sorted(por_ramo.items()):
            linhas.append(f"  ramo={ramo} evento={evento} execucoes={total}")
        linhas.append(f"  total listadas={len(execucoes)}")
    else:
        linhas.append("ERRO: " + erro[:300])
    linhas.append("")
    # Revisões das PRs mescladas recentes (somente o decisionamento).
    codigo, saida, erro = gh(["pr", "list", "--repo", REPO, "--state", "merged", "--limit", "15",
                              "--json", "number,reviewDecision,mergedAt,isDraft"])
    linhas.append("### prs_mescladas_recentes (gh pr list)")
    linhas.append(saida if codigo == 0 else "ERRO: " + erro[:300])
    linhas.append("")
    # Logs dos jobs da CI do SHA auditado (leitura de logs de execução já concluídos).
    for rotulo, job in [("ci_job_application", JOB_APP), ("ci_job_rabbitmq", JOB_RABBIT), ("ci_job_postgresql", JOB_PG)]:
        codigo, saida, erro = gh(["run", "view", "--repo", REPO, "--job", job, "--log"])
        destino = LOGS / f"{rotulo}.txt"
        destino.write_text(saida if codigo == 0 else "ERRO: " + erro[:500], encoding="utf-8")
        resumo[rotulo] = "ok" if codigo == 0 else "erro"
        linhas.append(f"### {rotulo}: {len(saida.splitlines()) if codigo == 0 else 0} linhas gravadas em {destino.name}")
    (LOGS / "github_leitura.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False))


if __name__ == "__main__":
    main()
