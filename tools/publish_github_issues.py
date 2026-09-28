"""Publish the canonical ArchCorp tasks as GitHub issue index entries.

Jira remains the source of truth. Existing Txx issues are reused so this script
can be rerun safely after an interruption.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEDULE = ROOT / "docs" / "CRONOGRAMA_EXECUCAO.md"
LEDGER = ROOT / "docs" / "GITHUB_ISSUES_SYNC.json"
REPOSITORY = "Roger-Quinelato/projetoAplicado7"
ISSUE_ID = re.compile(r"^T\d{2}$")


def gh(*args: str) -> str:
    result = subprocess.run(
        ["gh", *args], capture_output=True, text=True, encoding="utf-8", check=True
    )
    return result.stdout.strip()


def tasks() -> list[dict[str, str]]:
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

    LEDGER.write_text(json.dumps(found, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
