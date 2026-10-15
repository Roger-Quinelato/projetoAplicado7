"""Publish the canonical ArchCorp tasks as GitHub issue index entries.

Jira remains the source of truth. Existing Txx issues are reused so this script
can be rerun safely after an interruption.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEDULE = ROOT / "docs" / "CRONOGRAMA_EXECUCAO.md"
LEDGER = ROOT / "docs" / "GITHUB_ISSUES_SYNC.json"
REPOSITORY = "Roger-Quinelato/projetoAplicado7"
ISSUE_ID = re.compile(r"^T\d{2}$")
QUINZENA_END = ["2026-09-17", "2026-10-01", "2026-10-15", "2026-10-29", "2026-11-12", "2026-11-26", "2026-12-10"]
STATUS_COLORS = {"Em revisão": "fbca04", "Em andamento": "1f6feb", "Planejado": "d0d7de", "Aguardando": "a371f7"}


def gh(*args: str) -> str:
    """Executa o GitHub CLI e devolve a saída."""
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, encoding="utf-8", check=True
    )
    return result.stdout.strip()


def gh_api(method: str, endpoint: str, payload: dict) -> dict:
    """Chama a API do GitHub pelo CLI com corpo JSON."""
    result = subprocess.run(
        ["gh", "api", "--method", method, endpoint, "--input", "-"],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(result.stdout)


def tasks() -> list[dict[str, str]]:
    """Lê as 22 demandas canônicas do cronograma."""
    result = []
    for line in SCHEDULE.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6 or not ISSUE_ID.fullmatch(cells[0]):
            continue
        result.append(dict(zip(("id", "week", "demand", "priority", "status", "depends"), cells)))
    if len(result) != 22:
        raise RuntimeError(f"Expected 22 tasks, found {len(result)}")
    return result


def main() -> None:
    """Cria as issues ausentes, com marcos e etiquetas, sem duplicar as existentes."""
    existing = gh("issue", "list", "--repo", REPOSITORY, "--state", "all", "--limit", "200", "--json", "number,title,url")
    issues = json.loads(existing)
    found = {}
    for issue in issues:
        match = re.search(r"\bT\d{2}\b", issue["title"])
        if match:
            found[match.group()] = issue["url"]

    for task in tasks():
        task_id = task["id"]
        if task_id in found:
            print(f"{task_id}: existing {found[task_id]}")
            continue
        week = task["week"]
        first_week = int(re.search(r"S(\d+)", week).group(1))
        fortnight = (first_week + 1) // 2
        title = f"[{task_id}][{week}/Q{fortnight}] {task['demand'].split(';')[0]}"
        jira = f"https://projetooaplicado6.atlassian.net/browse/ARCH7-{int(task_id[1:])}"
        body = (
            f"## Demanda\n\n{task['demand']}\n\n"
            f"| Campo | Valor |\n|---|---|\n"
            f"| Tipo | Tarefa |\n| Tempo | {week}, Q{fortnight} |\n"
            f"| Prioridade | {task['priority']} |\n| Status em 27/09/2026 | {task['status']} |\n"
            f"| Dependências | {task['depends']} |\n\n"
            f"**Registro principal e aceite:** [ARCH7-{int(task_id[1:])}]({jira}).\n\n"
            f"[Cronograma S1–S14](https://github.com/{REPOSITORY}/blob/sobe-artefatos-cenario-4/docs/CRONOGRAMA_EXECUCAO.md) · "
            f"[PR de implementação](https://github.com/{REPOSITORY}/pull/2).\n\n"
            "O status nesta issue é um retrato do planejamento. Atualize o Jira antes de alterar o status aqui."
        )
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md", delete=False) as file:
            file.write(body)
            body_path = Path(file.name)
        try:
            url = gh("issue", "create", "--repo", REPOSITORY, "--title", title, "--body-file", str(body_path))
        finally:
            body_path.unlink(missing_ok=True)
        found[task_id] = url
        print(f"{task_id}: created {url}", flush=True)

    milestones = {item["title"]: item["number"] for item in json.loads(gh("api", f"repos/{REPOSITORY}/milestones?state=all&per_page=100"))}
    for fortnight, end_date in enumerate(QUINZENA_END, 1):
        title = f"Q{fortnight} · S{2 * fortnight - 1}–S{2 * fortnight}"
        if title not in milestones:
            due = (date.fromisoformat(end_date) + timedelta(days=1)).isoformat() + "T02:59:00Z"
            created = gh_api("POST", f"repos/{REPOSITORY}/milestones", {
                "title": title,
                "description": f"Quinzena Q{fortnight} do cronograma ArchCorp; prazo interno sujeito à validação docente.",
                "due_on": due,
            })
            milestones[title] = created["number"]
            print(f"milestone: {title}", flush=True)

    labels = {item["name"] for item in json.loads(gh("label", "list", "--repo", REPOSITORY, "--limit", "100", "--json", "name"))}
    required_labels = {"tipo:tarefa": ("1f6feb", "Tipo: tarefa")}
    for priority, color in (("Alta", "d73a4a"), ("Normal", "fbca04")):
        required_labels[f"prioridade:{priority.lower()}"] = (color, f"Prioridade: {priority}")
    for status, color in STATUS_COLORS.items():
        required_labels[f"status:{status.lower().replace(' ', '-')}"] = (color, f"Status do planejamento: {status}")
    for week in range(1, 15):
        required_labels[f"semana:S{week}"] = ("bfdadc", f"Semana S{week} do cronograma ArchCorp")
    for name, (color, description) in required_labels.items():
        if name not in labels:
            gh("label", "create", name, "--repo", REPOSITORY, "--color", color, "--description", description)
            print(f"label: {name}", flush=True)

    issues = json.loads(gh("issue", "list", "--repo", REPOSITORY, "--state", "all", "--limit", "200", "--json", "number,title,url,labels"))
    by_task = {}
    for issue in issues:
        match = re.search(r"\bT\d{2}\b", issue["title"])
        if match:
            by_task[match.group()] = issue
    for task in tasks():
        issue = by_task[task["id"]]
        first_week = int(re.search(r"S(\d+)", task["week"]).group(1))
        fortnight = (first_week + 1) // 2
        milestone_title = f"Q{fortnight} · S{2 * fortnight - 1}–S{2 * fortnight}"
        task_labels = {
            "tipo:tarefa",
            f"prioridade:{task['priority'].lower()}",
            f"status:{task['status'].lower().replace(' ', '-')}",
            *(f"semana:S{week}" for week in re.findall(r"S(\d+)", task["week"])),
        }
        current_labels = {label["name"] for label in issue["labels"]}
        gh_api("PATCH", f"repos/{REPOSITORY}/issues/{issue['number']}", {
            "milestone": milestones[milestone_title],
            "labels": sorted(current_labels | task_labels),
        })
        print(f"{task['id']}: Q{fortnight} + labels", flush=True)

    LEDGER.write_text(json.dumps(found, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
