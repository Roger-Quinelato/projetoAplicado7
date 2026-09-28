"""Publica, de forma retomável, as demandas canônicas no projeto Jira ARCH7.

Use somente depois de conferir o projeto e o cronograma. O arquivo de saída
registra as chaves confirmadas pelo Jira para evitar duplicações em retomadas.
"""

import json
import re
import subprocess
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / "docs" / "CRONOGRAMA_EXECUCAO.md"
OUTPUT = ROOT / "docs" / "JIRA_SYNC.json"
SITE = "projetooaplicado6.atlassian.net"
START = date(2026, 9, 4)


def main() -> None:
    if not OUTPUT.exists():
        raise SystemExit("Ledger local docs/JIRA_SYNC.json ausente; confira o Jira antes de publicar para evitar duplicatas")
    confirmed = json.loads(OUTPUT.read_text(encoding="utf-8"))
    rows = []
    for line in BACKLOG.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\| (T\d{2}) \| (S\d+(?:–S\d+)?) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$", line)
        if match:
            rows.append(match.groups())
    if len(rows) != 22:
        raise SystemExit(f"Esperadas 22 tarefas; encontradas {len(rows)}")
    for task_id, week, text, priority, status, dependencies in rows:
        if task_id in confirmed:
            print(f"{task_id}: existente {confirmed[task_id]}", flush=True)
            continue
        week_number = int(re.search(r"S(\d+)$", week).group(1))
        due = START + timedelta(days=week_number * 7 - 1)
        fortnight = (week_number + 1) // 2
        summary = f"[{task_id}][{week}] {text.split(';')[0]}"
        if len(summary) > 240:
            summary = summary[:237] + "..."
        description = (
            f"Tipo: tarefa\nPrioridade: {priority}\nStatus local em 27/09/2026: {status}\n"
            f"Semana: {week}; quinzena Q{fortnight}; prazo interno: {due.isoformat()}\n"
            f"Critério de aceite: {text}\nDependências canônicas: {dependencies}\n"
            "Fonte: docs/CRONOGRAMA_EXECUCAO.md no repositório Roger-Quinelato/projetoAplicado7. "
            "Premissas acadêmicas; sem acesso aos sistemas reais da Localiza."
        )
        cmd = ["twg", "jira", "workitem", "create", "--space", "ARCH7", "--type", "Tarefa",
               "--summary", summary, "--description", description, "--description-format", "plain",
               "--priority", {"Alta": "High", "Normal": "Medium", "Baixa": "Low", "Crítica": "Highest"}.get(priority, "Medium"),
               "--labels", f"archcorp,{task_id.lower()},s{week_number},q{fortnight}",
               "--field", f"duedate={due.isoformat()}", "--site", SITE]
        result = subprocess.run(cmd, text=True, capture_output=True, encoding="utf-8")
        if result.returncode:
            raise SystemExit(f"Falha {task_id}: {result.stdout}\n{result.stderr}")
        try:
            issue_key = json.loads(result.stdout)["issue"]["key"]
        except (ValueError, KeyError) as exc:
            raise SystemExit(f"Resposta inesperada {task_id}: {result.stdout}") from exc
        confirmed[task_id] = issue_key
        OUTPUT.write_text(json.dumps(confirmed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{task_id}: {issue_key}", flush=True)

    linked_file = ROOT / "docs" / "JIRA_LINKS.json"
    linked = set(json.loads(linked_file.read_text(encoding="utf-8"))) if linked_file.exists() else {"T01>T02"}
    for task_id, _, _, _, _, dependencies in rows:
        for predecessor in re.findall(r"T\d{2}", dependencies):
            pair = f"{predecessor}>{task_id}"
            if pair in linked:
                continue
            cmd = ["twg", "jira", "workitem", "link", "workitem", "--id", confirmed[predecessor],
                   "--target-id", confirmed[task_id], "--link-type-id", "Blocks", "--site", SITE]
            result = subprocess.run(cmd, text=True, capture_output=True, encoding="utf-8")
            if result.returncode:
                raise SystemExit(f"Falha vínculo {pair}: {result.stdout}\n{result.stderr}")
            linked.add(pair)
            linked_file.write_text(json.dumps(sorted(linked), indent=2) + "\n", encoding="utf-8")
            print(f"Vínculo {pair}", flush=True)

    status_file = ROOT / "docs" / "JIRA_STATUS.json"
    transitioned = set(json.loads(status_file.read_text(encoding="utf-8"))) if status_file.exists() else set()
    for task_id, _, _, _, status, _ in rows:
        if status not in {"Em andamento", "Em revisão"} or task_id in transitioned:
            continue
        cmd = ["twg", "jira", "workitem", "transition", "--id", confirmed[task_id],
               "--transition-id", "11", "--site", SITE]
        result = subprocess.run(cmd, text=True, capture_output=True, encoding="utf-8")
        if result.returncode:
            raise SystemExit(f"Falha status {task_id}: {result.stdout}\n{result.stderr}")
        transitioned.add(task_id)
        status_file.write_text(json.dumps(sorted(transitioned), indent=2) + "\n", encoding="utf-8")
        print(f"Status Em andamento {task_id}", flush=True)


if __name__ == "__main__":
    main()
